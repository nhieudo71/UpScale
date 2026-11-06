"""Nạp model ONNX bằng onnxruntime (chỉ CPU, offline). Đây là chỗ duy nhất biết về onnxruntime."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..domain.models import ErrorCode, UpscaleError

MODEL_FILE = "u2net.onnx"
# SHA256 của u2net.onnx (175.997.641 byte) tải từ rembg release v0.0.0 ngày 06/11/2026. Đây là hash tôi tính
# sau khi tải, GitHub không công bố hash để đối chiếu. Model lạ không được nạp vì onnxruntime phải phân tích file.
MODEL_SHA256 = "8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491"

MaskPredictor = Callable[[Any], Any]


def model_path(project_root: Path) -> Path:
    return project_root / "engine" / "background" / MODEL_FILE


def load_onnx_predictor(path: Path) -> MaskPredictor:
    """Raise UpscaleError(ENGINE_MISSING | ENGINE_FAILED). Thiếu onnxruntime thì ImportError nổi lên cho service xử lý.

    Job đầu tiên chậm hơn các job sau (đo được 1,6 đến 2,2 giây gồm đọc 176 MB, tính SHA256 và nạp model), chỉ
    trả một lần vì service giữ lại predictor.
    """
    try:
        data = path.read_bytes()  # đọc bytes để đường dẫn có ký tự Unicode không làm onnxruntime lỗi
    except FileNotFoundError:
        raise UpscaleError(
            ErrorCode.ENGINE_MISSING,
            f"Không tìm thấy model xóa nền: {path}. Xem README, mục Xóa nền.",
        ) from None
    except OSError as exc:
        raise UpscaleError(ErrorCode.ENGINE_FAILED, "Không đọc được file model xóa nền.", f"{type(exc).__name__}: {exc}") from exc
    digest = hashlib.sha256(data).hexdigest()
    if digest != MODEL_SHA256:
        raise UpscaleError(
            ErrorCode.ENGINE_FAILED,
            "File model xóa nền không đúng bản đã kiểm tra. Hãy tải lại u2net.onnx theo README.",
            f"sha256={digest}",
        )
    import onnxruntime as ort

    try:
        session = ort.InferenceSession(data, providers=["CPUExecutionProvider"])
    except Exception as exc:  # onnxruntime ném nhiều kiểu lỗi riêng cho file model hỏng
        raise UpscaleError(ErrorCode.ENGINE_FAILED, "Không nạp được model xóa nền.", f"{type(exc).__name__}: {exc}") from exc
    input_name = session.get_inputs()[0].name

    def predict(batch: Any) -> Any:
        return session.run(None, {input_name: batch})[0]  # đầu ra đầu tiên là mặt nạ đã gộp của U²-Net

    return predict
