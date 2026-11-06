"""Pillow: đọc kích thước và kiểm tra ảnh. File gốc chỉ được mở để đọc."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..domain.models import ErrorCode, ImageInfo, UpscaleError

_ALLOWED_FORMATS = {"PNG", "JPEG"}
_UNREADABLE_MSG = "File này không phải ảnh PNG/JPG hợp lệ hoặc đã bị hỏng."


def inspect_image(path: str) -> ImageInfo:
    """Trả về ImageInfo, hoặc raise UpscaleError(IMAGE_UNREADABLE)."""
    try:
        with Image.open(Path(path)) as img:
            fmt = img.format or ""
            width, height = img.size  # chỉ đọc header, chưa giải mã toàn ảnh
            if fmt not in _ALLOWED_FORMATS or width < 1 or height < 1:
                raise UpscaleError(ErrorCode.IMAGE_UNREADABLE, _UNREADABLE_MSG, f"format={fmt!r} size={width}x{height}")
            img.verify()  # phát hiện file cắt cụt; sau lệnh này đối tượng img không dùng lại được
    except UpscaleError:
        raise
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        # UnidentifiedImageError và FileNotFoundError đều là OSError. Pillow đôi khi ném
        # SyntaxError cho PNG hỏng.
        raise UpscaleError(ErrorCode.IMAGE_UNREADABLE, _UNREADABLE_MSG, f"{type(exc).__name__}: {exc}") from exc
    return ImageInfo(path=str(path), width=width, height=height, format=fmt)
