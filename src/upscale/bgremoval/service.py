"""BackgroundRemovalService: điều phối một job xóa nền. Cùng dạng với UpscaleService để giao diện dùng chung
EventBridge, thanh tiến độ và hộp thoại hủy: sự kiện là JobEvent, lỗi là UpscaleError.

on_event được gọi từ luồng worker. Model chỉ chạy trên CPU và không cần mạng. Một lần chạy model không ngắt
giữa chừng được, nên hủy chỉ có hiệu lực giữa các bước.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from PIL import Image

from ..domain.models import ErrorCode, EventType, ImageInfo, JobEvent, UpscaleError
from ..domain.rules import check_output_limit
from ..infra.config import Config
from ..infra.image_io import inspect_image
from . import matting
from .rules import output_candidates
from .session import MaskPredictor, load_onnx_predictor, model_path

log = logging.getLogger(__name__)

EventCallback = Callable[[JobEvent], None]
PredictorLoader = Callable[[Path], MaskPredictor]


class BackgroundRemovalService:
    def __init__(self, config: Config, predictor_loader: PredictorLoader | None = None) -> None:
        """predictor_loader chỉ dùng cho test (model giả). Mặc định nạp u2net.onnx bằng onnxruntime."""
        self._config = config
        self._loader: PredictorLoader = predictor_loader or load_onnx_predictor
        self._predictor: MaskPredictor | None = None
        self._lock = threading.Lock()
        self._job_id: str | None = None
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- API công khai ----
    def inspect_image(self, path: str) -> ImageInfo:
        return inspect_image(path)

    def start(self, source_path: str, on_event: EventCallback) -> str:
        """Bắt đầu job ở luồng nền và trả job_id. Mọi lỗi sau đó đến qua sự kiện `failed`.

        Raise UpscaleError(BUSY) nếu đang có job.
        """
        with self._lock:
            if self._job_id is not None:
                raise UpscaleError(ErrorCode.BUSY, "Đang xử lý một ảnh khác. Hãy chờ xong hoặc hủy.")
            job_id = uuid.uuid4().hex[:8]
            self._job_id = job_id
            self._cancel = threading.Event()
            self._thread = threading.Thread(
                target=self._run, args=(job_id, source_path, on_event, self._cancel), name=f"bg-{job_id}", daemon=True
            )
            self._thread.start()
        return job_id

    def cancel(self, job_id: str) -> None:
        with self._lock:
            if self._job_id == job_id:
                self._cancel.set()

    def shutdown(self, timeout_s: float = 10.0) -> None:
        with self._lock:
            self._cancel.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout_s)

    # ---- Nội bộ ----
    def _emit(self, on_event: EventCallback, event: JobEvent) -> None:
        try:
            on_event(event)
        except Exception:  # lỗi của giao diện không được làm hỏng job
            log.exception("on_event ném ngoại lệ")

    @staticmethod
    def _check_cancel(cancel: threading.Event) -> None:
        if cancel.is_set():
            raise UpscaleError(ErrorCode.CANCELLED, "Đã hủy xử lý.")

    def _get_predictor(self) -> MaskPredictor:
        if self._predictor is None:
            try:
                self._predictor = self._loader(model_path(self._config.project_root))
            except ImportError as exc:
                raise UpscaleError(
                    ErrorCode.ENGINE_MISSING,
                    "Thiếu thư viện xóa nền. Chạy: python -m pip install -r requirements.txt",
                    f"{type(exc).__name__}: {exc}",
                ) from exc
        return self._predictor

    def _run(self, job_id: str, source_path: str, on_event: EventCallback, cancel: threading.Event) -> None:
        started = time.monotonic()
        tmp: Path | None = None
        try:
            self._emit(on_event, JobEvent(job_id, EventType.STARTED))
            info = inspect_image(source_path)
            # Cùng giới hạn điểm ảnh với upscale vì ảnh RGBA nằm trọn trong RAM.
            check_output_limit(info.width, info.height, 1, self._config.max_output_pixels)
            self._check_cancel(cancel)

            predictor = self._get_predictor()
            self._emit(on_event, JobEvent(job_id, EventType.PROGRESS, percent=20.0))
            self._check_cancel(cancel)

            src = Path(source_path)
            with Image.open(src) as opened:
                image = opened.convert("RGBA")
            try:
                prediction = predictor(matting.preprocess(image))
                mask = matting.mask_from_prediction(prediction, image.size)
            except UpscaleError:
                raise
            except Exception as exc:  # lỗi của model hoặc numpy: báo gọn, chi tiết vào log
                raise UpscaleError(
                    ErrorCode.ENGINE_FAILED, "Model xóa nền dừng với lỗi. Ảnh gốc không bị ảnh hưởng.", f"{type(exc).__name__}: {exc}"
                ) from exc
            self._emit(on_event, JobEvent(job_id, EventType.PROGRESS, percent=80.0))
            self._check_cancel(cancel)

            result = matting.apply_mask(image, mask)
            tmp = src.with_name(f".{src.stem}_nobg.{job_id}.tmp.png")
            result.save(tmp, format="PNG")
            final = self._publish(tmp, src)
            tmp = None
            duration_ms = int((time.monotonic() - started) * 1000)
            log.info("Job %s xóa nền xong: %s (%dx%d) trong %d ms", job_id, final, info.width, info.height, duration_ms)
            self._emit(
                on_event,
                JobEvent(job_id, EventType.DONE, percent=100.0, output_path=str(final),
                         output_w=info.width, output_h=info.height, duration_ms=duration_ms),
            )
        except UpscaleError as exc:
            log.warning("Job %s xóa nền lỗi %s: %s | %s", job_id, exc.code.value, exc.message, exc.detail)
            self._emit(on_event, JobEvent(job_id, EventType.FAILED, code=exc.code, message=exc.message))
        except Exception as exc:  # lớp bảo vệ cuối: luôn phát đúng một sự kiện kết thúc
            log.exception("Job %s xóa nền lỗi không lường trước", job_id)
            self._emit(on_event, JobEvent(job_id, EventType.FAILED, code=ErrorCode.ENGINE_FAILED,
                                          message=f"Có lỗi không mong đợi ({type(exc).__name__}). Xem file log để biết chi tiết."))
        finally:
            if tmp is not None:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    log.warning("Không xóa được file tạm %s", tmp)
            with self._lock:
                self._job_id = None

    @staticmethod
    def _publish(tmp: Path, src: Path) -> Path:
        """Đổi tên file tạm thành `<tên>_nobg.png`. os.rename trên Windows báo FileExistsError khi đích đã có,
        nên vòng lặp này không bao giờ ghi đè file của người dùng."""
        for candidate in output_candidates(src):
            try:
                os.rename(tmp, candidate)
                return candidate
            except FileExistsError:
                continue
            except OSError as exc:
                raise UpscaleError(
                    ErrorCode.ENGINE_FAILED,
                    "Không lưu được ảnh kết quả vào thư mục chứa ảnh gốc. Kiểm tra quyền ghi của thư mục.",
                    f"{type(exc).__name__}: {exc}",
                ) from exc
        raise AssertionError("output_candidates là vô hạn")  # pragma: no cover
