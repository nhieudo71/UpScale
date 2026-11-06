"""Tiền xử lý và hậu xử lý cho model U²-Net (u2net, cùng cách xử lý với u2netp và silueta). Không I/O, không biết gì về onnxruntime.

numpy được import trong từng hàm để thiếu numpy thì app vẫn mở được; lỗi chỉ hiện khi người dùng bấm Xóa nền.
"""
from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops

INPUT_SIZE = 320  # u2net nhận ảnh 320 x 320 (đã kiểm: input [1, 3, 320, 320])
_MEAN = (0.485, 0.456, 0.406)
_STD = (0.229, 0.224, 0.225)


def preprocess(image: Image.Image) -> Any:
    """Ảnh bất kỳ -> tensor float32 hình (1, 3, 320, 320), chuẩn hóa theo ImageNet như rembg."""
    import numpy as np

    resized = image.convert("RGB").resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.LANCZOS)
    pixels = np.asarray(resized, dtype=np.float32)
    pixels = pixels / max(float(pixels.max()), 1e-6)  # ảnh đen hoàn toàn thì không chia cho 0
    pixels = (pixels - np.array(_MEAN, dtype=np.float32)) / np.array(_STD, dtype=np.float32)
    return np.ascontiguousarray(pixels.transpose(2, 0, 1)[np.newaxis], dtype=np.float32)


def mask_from_prediction(prediction: Any, size: tuple[int, int]) -> Image.Image:
    """Đầu ra model (1, 1, 320, 320) -> mặt nạ 'L' cỡ `size`, 255 = giữ lại, 0 = xóa."""
    import numpy as np

    grid = np.squeeze(np.asarray(prediction, dtype=np.float32))
    if grid.ndim != 2:
        raise ValueError(f"đầu ra model có hình {np.asarray(prediction).shape}, cần (1, 1, H, W)")
    low, high = float(grid.min()), float(grid.max())
    grid = (grid - low) / max(high - low, 1e-6)
    mask = Image.fromarray((grid * 255).round().astype(np.uint8))
    return mask.resize(size, Image.Resampling.LANCZOS)


def apply_mask(image: Image.Image, mask: Image.Image) -> Image.Image:
    """RGBA có alpha = mặt nạ. Ảnh gốc đã có alpha thì nhân với mặt nạ, vùng trong suốt sẵn vẫn trong suốt."""
    rgba = image.convert("RGBA")
    rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), mask))
    return rgba
