"""Đọc config.toml bằng tomllib. Thiếu file hoặc giá trị sai thì dùng mặc định và ghi log."""
from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# config.py nằm ở <root>/src/upscale/infra/ nên gốc dự án là parents[3].
PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Config:
    project_root: Path = PROJECT_ROOT
    gpu_id: int = 0
    tile: int = 0  # 0 = để engine tự chọn
    max_output_pixels: int = 0  # 0 = không giới hạn. Giá trị đã đo cho máy này là 150000000, xem DECISIONS.md
    engine_timeout_s: int = 600

    @property
    def engine_dir(self) -> Path:
        return self.project_root / "engine" / "realesrgan"

    @property
    def engine_exe(self) -> Path:
        return self.engine_dir / "realesrgan-ncnn-vulkan.exe"

    @property
    def models_dir(self) -> Path:
        return self.engine_dir / "models"

    @property
    def log_dir(self) -> Path:
        return self.project_root / "logs"


# Khóa số nguyên hợp lệ và giá trị nhỏ nhất của từng khóa.
_INT_KEYS: dict[str, int] = {
    "gpu_id": 0,
    "tile": 0,
    "max_output_pixels": 0,
    "engine_timeout_s": 1,
}


def load_config(path: Path | None = None, project_root: Path = PROJECT_ROOT) -> Config:
    config_path = path or project_root / "config.toml"
    try:
        with config_path.open("rb") as handle:
            raw = tomllib.load(handle)
    except FileNotFoundError:
        log.info("Không có %s, dùng cấu hình mặc định", config_path)
        return Config(project_root=project_root)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("Không đọc được %s (%s), dùng cấu hình mặc định", config_path, exc)
        return Config(project_root=project_root)

    values: dict[str, int] = {}
    for key, minimum in _INT_KEYS.items():
        if key not in raw:
            continue
        value = raw[key]
        # bool là con của int trong Python nên phải loại riêng.
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            log.warning("Bỏ qua %s=%r trong config.toml (cần số nguyên >= %d)", key, value, minimum)
            continue
        values[key] = value
    return Config(project_root=project_root, **values)
