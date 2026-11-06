"""Điểm vào: python run.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from upscale.ui.app import main  # noqa: E402  (phải import sau khi thêm src vào sys.path)

if __name__ == "__main__":
    sys.exit(main())
