"""Thêm src/ vào sys.path để test import được `upscale` mà không cần cài gói."""
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
