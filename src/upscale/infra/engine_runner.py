"""Chạy engine bằng tiến trình con. Đây là chỗ duy nhất biết về subprocess."""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import IO

from ..domain.models import ErrorCode, UpscaleError
from ..domain.rules import classify_engine_failure, parse_progress

log = logging.getLogger(__name__)

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_STDERR_TAIL_LINES = 20

_MESSAGES = {
    ErrorCode.OUT_OF_VRAM: "Không đủ bộ nhớ GPU khi xử lý ảnh này. Hãy thử hệ số 2x hoặc đóng ứng dụng đang dùng GPU.",
    ErrorCode.ENGINE_FAILED: "Engine dừng với lỗi. Ảnh gốc không bị ảnh hưởng.",
}


def _pump_stderr(stream: IO[str], tail: deque[str], on_progress: Callable[[float], None]) -> None:
    """Đọc stderr theo dòng: dòng phần trăm đi vào on_progress, dòng khác giữ lại để chẩn đoán."""
    last: float | None = None
    for raw in stream:
        line = raw.strip()
        if not line:
            continue
        percent = parse_progress(line)
        if percent is None:
            tail.append(line)
        elif percent != last:
            last = percent
            try:
                on_progress(percent)
            except Exception:  # callback của người gọi không được làm chết luồng đọc
                log.exception("on_progress ném ngoại lệ")


def _stop(proc: subprocess.Popen[str]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def run_engine(
    cmd_prefix: Sequence[str],
    src: Path,
    dst: Path,
    model: str,
    scale: int,
    gpu_id: int,
    tile: int,
    models_dir: Path | None,
    timeout_s: float,
    on_progress: Callable[[float], None],
    cancel: threading.Event,
) -> None:
    """Chạy engine cho tới khi xong. Thành công khi returncode == 0 và dst tồn tại.

    Raise UpscaleError(ENGINE_MISSING | OUT_OF_VRAM | ENGINE_FAILED | CANCELLED).
    Đối số truyền dạng danh sách, không dùng shell, nên đường dẫn người dùng chọn không bị diễn giải.
    """
    cmd = [*cmd_prefix, "-i", str(src), "-o", str(dst), "-n", model, "-s", str(scale), "-g", str(gpu_id)]
    if models_dir is not None:
        cmd += ["-m", str(models_dir)]
    if tile > 0:
        cmd += ["-t", str(tile)]
    log.info("Chạy engine: %s", cmd)

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_CREATE_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise UpscaleError(
            ErrorCode.ENGINE_MISSING, f"Không tìm thấy engine: {cmd[0]}. Hãy chép lại thư mục engine\\realesrgan.", str(exc)
        ) from exc
    except OSError as exc:
        raise UpscaleError(ErrorCode.ENGINE_FAILED, _MESSAGES[ErrorCode.ENGINE_FAILED], str(exc)) from exc

    tail: deque[str] = deque(maxlen=_STDERR_TAIL_LINES)
    assert proc.stderr is not None  # stderr=PIPE luôn có luồng
    reader = threading.Thread(target=_pump_stderr, args=(proc.stderr, tail, on_progress), daemon=True)
    reader.start()

    deadline = time.monotonic() + timeout_s
    try:
        while True:
            if cancel.is_set():
                _stop(proc)
                raise UpscaleError(ErrorCode.CANCELLED, "Đã hủy xử lý.")
            if time.monotonic() > deadline:
                _stop(proc)
                raise UpscaleError(
                    ErrorCode.ENGINE_FAILED,
                    "Engine chạy quá thời gian cho phép nên đã bị dừng. Hãy thử hệ số 2x.",
                    f"timeout sau {timeout_s}s",
                )
            try:
                proc.wait(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                continue
    finally:
        if proc.poll() is None:  # đường thoát bất thường: không để tiến trình mồ côi
            _stop(proc)
        reader.join(timeout=2)
        try:
            proc.stderr.close()  # tránh rò rỉ file handle (ResourceWarning)
        except OSError:
            log.warning("Không đóng được stderr của engine")

    stderr_tail = "\n".join(tail)
    if proc.returncode != 0:
        code = classify_engine_failure(stderr_tail)
        raise UpscaleError(code, _MESSAGES[code], f"returncode={proc.returncode}\n{stderr_tail}")
    if not dst.exists():
        raise UpscaleError(ErrorCode.ENGINE_FAILED, _MESSAGES[ErrorCode.ENGINE_FAILED], f"thoát mã 0 nhưng không có {dst}\n{stderr_tail}")
