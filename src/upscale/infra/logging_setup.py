"""Ghi log ra logs/app.log, xoay vòng. Chi tiết kỹ thuật chỉ vào đây, không hiện cho người dùng."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: Path) -> Path:
    """Gắn handler vào logger "upscale". Gọi nhiều lần vẫn chỉ gắn một handler."""
    log_file = log_dir / "app.log"
    logger = logging.getLogger("upscale")
    logger.setLevel(logging.INFO)
    if any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        return log_file
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    except OSError:
        # Không ghi được log thì app vẫn phải chạy.
        handler = logging.NullHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return log_file
