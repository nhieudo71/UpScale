"""Quy tắc thuần: kích thước, đặt tên file, parse tiến độ, phân loại lỗi engine."""
from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from .models import ErrorCode, UpscaleError

# Engine in phần trăm theo locale máy: "25,00%" (dấu phẩy) hoặc "25.00%" (dấu chấm).
_PROGRESS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")

# Dấu hiệu hết VRAM trong stderr của engine. CHƯA kiểm chứng trên máy thật vì chưa
# làm engine hết bộ nhớ; chỉ là suy đoán theo thông báo lỗi Vulkan thường gặp.
_OOM_MARKERS = (
    "out of memory",
    "vkallocatememory",
    "vk_error_out_of_device_memory",
    "vk_error_out_of_host_memory",
)


def output_size(width: int, height: int, scale: int) -> tuple[int, int]:
    return width * scale, height * scale


def check_output_limit(width: int, height: int, scale: int, max_pixels: int) -> None:
    """Chặn trước khi chạy. max_pixels = 0 nghĩa là chưa đặt giới hạn (chưa đo)."""
    out_w, out_h = output_size(width, height, scale)
    if max_pixels > 0 and out_w * out_h > max_pixels:
        raise UpscaleError(
            ErrorCode.OUTPUT_TOO_LARGE,
            f"Ảnh kết quả sẽ có kích thước {out_w} x {out_h}, vượt giới hạn máy này "
            "xử lý an toàn. Hãy thử hệ số nhỏ hơn.",
        )


def parse_progress(line: str) -> float | None:
    """Trả về phần trăm 0..100, hoặc None nếu dòng không phải dòng tiến độ."""
    match = _PROGRESS_RE.search(line)
    if match is None:
        return None
    value = float(match.group(1).replace(",", "."))
    return min(max(value, 0.0), 100.0)


def classify_engine_failure(stderr_tail: str) -> ErrorCode:
    lowered = stderr_tail.lower()
    if any(marker in lowered for marker in _OOM_MARKERS):
        return ErrorCode.OUT_OF_VRAM
    return ErrorCode.ENGINE_FAILED


def output_candidates(source: Path, scale: int) -> Iterator[Path]:
    """`<tên>_x<scale>.png`, rồi `<tên>_x<scale>_2.png`, `_3`... Không bao giờ ghi đè."""
    base = f"{source.stem}_x{scale}"
    yield source.with_name(f"{base}.png")
    n = 2
    while True:
        yield source.with_name(f"{base}_{n}.png")
        n += 1
