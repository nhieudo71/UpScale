"""Kiểu dữ liệu thuần của UpScale. Không I/O, không import từ lớp khác."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

SUPPORTED_SCALES: tuple[int, ...] = (2, 4)
DEFAULT_MODEL = "photo"


class ErrorCode(str, Enum):
    """Mã lỗi khớp docs/ARCHITECTURE.md mục 3.1. BUSY là lớp bảo vệ lập trình."""

    IMAGE_UNREADABLE = "IMAGE_UNREADABLE"
    ENGINE_MISSING = "ENGINE_MISSING"
    OUTPUT_TOO_LARGE = "OUTPUT_TOO_LARGE"
    OUT_OF_VRAM = "OUT_OF_VRAM"
    ENGINE_FAILED = "ENGINE_FAILED"
    CANCELLED = "CANCELLED"
    BUSY = "BUSY"


class EventType(str, Enum):
    STARTED = "started"
    PROGRESS = "progress"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class ModelInfo:
    key: str
    label: str
    engine_name: str


MODELS: dict[str, ModelInfo] = {
    "photo": ModelInfo("photo", "Ảnh thật", "realesrgan-x4plus"),
    "anime": ModelInfo("anime", "Anime", "realesrgan-x4plus-anime"),
}


@dataclass(frozen=True)
class ImageInfo:
    path: str
    width: int
    height: int
    format: str


@dataclass(frozen=True)
class UpscaleRequest:
    source_path: str
    scale: int = 4
    model: str = DEFAULT_MODEL
    gpu_id: int | None = None  # None = dùng gpu_id trong config.toml

    def __post_init__(self) -> None:
        # Giao diện không thể tạo giá trị sai, nên đây là lỗi lập trình (ValueError).
        if self.scale not in SUPPORTED_SCALES:
            raise ValueError(f"scale phải thuộc {SUPPORTED_SCALES}, nhận {self.scale!r}")
        if self.model not in MODELS:
            raise ValueError(f"model phải thuộc {tuple(MODELS)}, nhận {self.model!r}")
        if self.gpu_id is not None and self.gpu_id < 0:
            raise ValueError("gpu_id phải >= 0")


@dataclass(frozen=True)
class JobEvent:
    job_id: str
    type: EventType
    percent: float | None = None
    output_path: str | None = None
    output_w: int | None = None
    output_h: int | None = None
    duration_ms: int | None = None
    code: ErrorCode | None = None
    message: str | None = None


class UpscaleError(Exception):
    """Lỗi có mã và thông báo tiếng Việt cho người dùng. `detail` chỉ để ghi log."""

    def __init__(self, code: ErrorCode, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail
