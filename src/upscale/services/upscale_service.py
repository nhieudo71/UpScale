"""UpscaleService: điều phối một job upscale. Giao diện chỉ gọi lớp này, không gọi engine trực tiếp.

on_event được gọi từ luồng worker, không phải luồng Tkinter. Phía giao diện phải
chuyển sự kiện về luồng chính (xem ui/event_bridge.py).
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from pathlib import Path

from PIL import Image

from ..domain.models import (
    MODELS,
    ErrorCode,
    EventType,
    ImageInfo,
    JobEvent,
    ModelInfo,
    UpscaleError,
    UpscaleRequest,
)
from ..domain.rules import check_output_limit, output_candidates, output_size
from ..infra.config import Config
from ..infra.engine_runner import run_engine
from ..infra.image_io import inspect_image

log = logging.getLogger(__name__)

EventCallback = Callable[[JobEvent], None]

ENGINE_NATIVE_SCALE = 4  # hệ số gốc của cả hai model (realesrgan-x4plus và -anime)


class UpscaleService:
    def __init__(self, config: Config, engine_cmd: Sequence[str] | None = None) -> None:
        """engine_cmd chỉ dùng cho test (engine giả). Mặc định chạy realesrgan-ncnn-vulkan.exe."""
        self._config = config
        self._custom_engine = engine_cmd is not None
        self._engine_cmd: list[str] = list(engine_cmd) if engine_cmd else [str(config.engine_exe)]
        self._lock = threading.Lock()
        self._job_id: str | None = None
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- API công khai ----
    def inspect_image(self, path: str) -> ImageInfo:
        return inspect_image(path)

    def list_models(self) -> list[ModelInfo]:
        return list(MODELS.values())

    def start(self, req: UpscaleRequest, on_event: EventCallback) -> str:
        """Bắt đầu job ở luồng nền và trả job_id. Mọi lỗi sau đó đến qua sự kiện `failed`.

        Raise UpscaleError(BUSY) nếu đang có job: GPU 4 GB không chạy song song.
        """
        with self._lock:
            if self._job_id is not None:
                raise UpscaleError(ErrorCode.BUSY, "Đang xử lý một ảnh khác. Hãy chờ xong hoặc hủy.")
            job_id = uuid.uuid4().hex[:8]
            self._job_id = job_id
            self._cancel = threading.Event()
            self._thread = threading.Thread(
                target=self._run, args=(job_id, req, on_event, self._cancel), name=f"job-{job_id}", daemon=True
            )
            self._thread.start()
        return job_id

    def cancel(self, job_id: str) -> None:
        with self._lock:
            if self._job_id == job_id:
                self._cancel.set()

    def shutdown(self, timeout_s: float = 10.0) -> None:
        """Gọi khi đóng app: hủy job đang chạy và chờ tiến trình con kết thúc."""
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

    def _run(self, job_id: str, req: UpscaleRequest, on_event: EventCallback, cancel: threading.Event) -> None:
        started = time.monotonic()
        tmp: Path | None = None
        scratch: Path | None = None
        try:
            self._emit(on_event, JobEvent(job_id, EventType.STARTED))
            info = inspect_image(req.source_path)
            check_output_limit(info.width, info.height, req.scale, self._config.max_output_pixels)
            # Model x4plus chỉ có bản x4: `-s 2` cho ảnh sai nội dung (tile bị xé) dù đúng kích thước,
            # nên 2x = chạy 4x rồi thu nhỏ. Ảnh trung gian 4x vẫn phải nằm trong giới hạn của máy.
            engine_scale = max(req.scale, ENGINE_NATIVE_SCALE)
            try:
                check_output_limit(info.width, info.height, engine_scale, self._config.max_output_pixels)
            except UpscaleError as exc:
                raise UpscaleError(
                    ErrorCode.OUTPUT_TOO_LARGE,
                    "Ảnh này quá lớn để phóng 2x an toàn trên máy này vì engine phải xử lý ở 4x trước. "
                    "Hãy thu nhỏ ảnh gốc rồi thử lại.",
                    exc.message,
                ) from exc
            model = MODELS[req.model]
            self._check_engine_files(model)

            src = Path(req.source_path)
            # File tạm nằm cạnh đích để rename sau đó cùng ổ đĩa, và có đuôi .png vì engine chọn định dạng theo đuôi.
            tmp = src.with_name(f".{src.stem}_x{req.scale}.{job_id}.tmp.png")
            scratch = self._ascii_scratch(tmp, job_id)
            run_engine(
                self._engine_cmd,
                src,
                scratch or tmp,
                model.engine_name,
                engine_scale,
                req.gpu_id if req.gpu_id is not None else self._config.gpu_id,
                self._config.tile,
                None if self._custom_engine else self._config.models_dir,
                float(self._config.engine_timeout_s),
                lambda pct: self._emit(on_event, JobEvent(job_id, EventType.PROGRESS, percent=pct)),
                cancel,
            )

            if scratch is not None:
                shutil.move(scratch, tmp)  # về cạnh ảnh gốc để bước đổi tên bên dưới cùng ổ đĩa
                scratch = None

            expected = output_size(info.width, info.height, req.scale)
            engine_expected = output_size(info.width, info.height, engine_scale)
            actual = self._read_size(tmp)
            if actual != engine_expected:
                raise UpscaleError(
                    ErrorCode.ENGINE_FAILED,
                    "Engine tạo ra ảnh sai kích thước nên không lưu kết quả. Ảnh gốc không bị ảnh hưởng.",
                    f"mong đợi {engine_expected}, nhận {actual}",
                )
            if engine_expected != expected:
                self._downscale(tmp, expected)
            final = self._publish(tmp, src, req.scale)
            tmp = None
            duration_ms = int((time.monotonic() - started) * 1000)
            log.info("Job %s xong: %s (%dx%d) trong %d ms", job_id, final, expected[0], expected[1], duration_ms)
            self._emit(
                on_event,
                JobEvent(job_id, EventType.DONE, percent=100.0, output_path=str(final),
                         output_w=expected[0], output_h=expected[1], duration_ms=duration_ms),
            )
        except UpscaleError as exc:
            log.warning("Job %s lỗi %s: %s | %s", job_id, exc.code.value, exc.message, exc.detail)
            self._emit(on_event, JobEvent(job_id, EventType.FAILED, code=exc.code, message=exc.message))
        except Exception as exc:  # lớp bảo vệ cuối: luôn phát đúng một sự kiện kết thúc
            log.exception("Job %s lỗi không lường trước", job_id)
            self._emit(on_event, JobEvent(job_id, EventType.FAILED, code=ErrorCode.ENGINE_FAILED,
                                          message=f"Có lỗi không mong đợi ({type(exc).__name__}). Xem file log để biết chi tiết."))
        finally:
            for leftover in (tmp, scratch):
                if leftover is not None:
                    try:
                        leftover.unlink(missing_ok=True)
                    except OSError:
                        log.warning("Không xóa được file tạm %s", leftover)
            with self._lock:
                self._job_id = None

    @staticmethod
    def _downscale(path: Path, size: tuple[int, int]) -> None:
        """Thu ảnh 4x của engine về đúng kích thước yêu cầu (ghi đè file tạm)."""
        with Image.open(path) as img:
            resized = img.resize(size, Image.Resampling.LANCZOS)
        resized.save(path, format="PNG")

    @staticmethod
    def _ascii_scratch(tmp: Path, job_id: str) -> Path | None:
        """Engine thật crash (mã 0xC0000409) khi đường dẫn ĐẦU RA có ký tự không phải ASCII, vd thư
        mục "_ĐẢNG" (tái hiện ngày 06/11, xem docs/DECISIONS.md). Đường dẫn đầu vào Unicode thì chạy được.

        Trả về đường dẫn ASCII để engine ghi vào, hoặc None nếu tmp đã là ASCII.
        """
        if str(tmp).isascii():
            return None
        scratch = Path(tempfile.gettempdir()) / f"upscale_{job_id}.png"
        if not str(scratch).isascii():
            raise UpscaleError(
                ErrorCode.ENGINE_FAILED,
                "Engine không ghi được ảnh vào thư mục có tên chứa ký tự đặc biệt. "
                "Hãy chép ảnh sang thư mục có tên không dấu rồi thử lại.",
                f"cả {tmp} lẫn {scratch} đều không phải ASCII",
            )
        return scratch

    def _check_engine_files(self, model: ModelInfo) -> None:
        if self._custom_engine:
            return
        required = [
            self._config.engine_exe,
            self._config.models_dir / f"{model.engine_name}.param",
            self._config.models_dir / f"{model.engine_name}.bin",
        ]
        for path in required:
            if not path.exists():
                raise UpscaleError(
                    ErrorCode.ENGINE_MISSING,
                    f"Không tìm thấy: {path}. Hãy chép lại thư mục engine\\realesrgan.",
                )

    @staticmethod
    def _read_size(path: Path) -> tuple[int, int] | None:
        try:
            with Image.open(path) as img:
                return img.size
        except (OSError, ValueError, SyntaxError):
            return None

    @staticmethod
    def _publish(tmp: Path, src: Path, scale: int) -> Path:
        """Đổi tên file tạm thành tên đích mà không ghi đè file có sẵn.

        os.rename trên Windows báo FileExistsError khi đích đã có (khác os.replace), nên
        vòng lặp này không bao giờ ghi đè file của người dùng.
        """
        for candidate in output_candidates(src, scale):
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

