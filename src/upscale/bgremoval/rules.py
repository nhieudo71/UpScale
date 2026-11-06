"""Quy tắc thuần của tính năng xóa nền: đặt tên file kết quả."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path


def output_candidates(source: Path) -> Iterator[Path]:
    """`<tên>_nobg.png`, rồi `<tên>_nobg_2.png`, `_3`... Không bao giờ ghi đè."""
    base = f"{source.stem}_nobg"
    yield source.with_name(f"{base}.png")
    n = 2
    while True:
        yield source.with_name(f"{base}_{n}.png")
        n += 1
