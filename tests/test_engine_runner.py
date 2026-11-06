import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from upscale.domain.models import ErrorCode, UpscaleError
from upscale.infra.engine_runner import run_engine

FAKE = [sys.executable, str(Path(__file__).with_name("fake_engine.py"))]


class RunEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.src = self.dir / "in.png"
        Image.new("RGB", (10, 8), (200, 10, 10)).save(self.src)
        self.dst = self.dir / "out.png"

    def _run(self, mode: str, *, timeout: float = 20, cancel: threading.Event | None = None,
             cmd: list[str] | None = None, progress: list[float] | None = None) -> None:
        with mock.patch.dict(os.environ, {"FAKE_MODE": mode}):
            run_engine(cmd or FAKE, self.src, self.dst, "realesrgan-x4plus", 4, 0, 0, None, timeout,
                       (progress.append if progress is not None else (lambda _p: None)),
                       cancel or threading.Event())

    def test_success_reports_progress_and_creates_output(self) -> None:
        seen: list[float] = []
        self._run("ok", progress=seen)
        self.assertTrue(self.dst.exists())
        self.assertEqual(seen, [0.0, 25.0, 100.0])
        with Image.open(self.dst) as img:
            self.assertEqual(img.size, (40, 32))

    def test_dot_decimal_progress(self) -> None:
        seen: list[float] = []
        self._run("dot", progress=seen)
        self.assertIn(25.0, seen)

    def test_nonzero_exit_is_engine_failed(self) -> None:
        with self.assertRaises(UpscaleError) as ctx:
            self._run("fail")
        self.assertEqual(ctx.exception.code, ErrorCode.ENGINE_FAILED)
        self.assertIn("some unexpected error", ctx.exception.detail)

    def test_oom_is_classified(self) -> None:
        with self.assertRaises(UpscaleError) as ctx:
            self._run("oom")
        self.assertEqual(ctx.exception.code, ErrorCode.OUT_OF_VRAM)

    def test_exit_zero_without_output_is_failure(self) -> None:
        with self.assertRaises(UpscaleError) as ctx:
            self._run("nooutput")
        self.assertEqual(ctx.exception.code, ErrorCode.ENGINE_FAILED)

    def test_missing_executable(self) -> None:
        with self.assertRaises(UpscaleError) as ctx:
            self._run("ok", cmd=[str(self.dir / "khong-co.exe")])
        self.assertEqual(ctx.exception.code, ErrorCode.ENGINE_MISSING)

    def test_timeout_stops_process(self) -> None:
        began = time.monotonic()
        with self.assertRaises(UpscaleError) as ctx:
            self._run("hang", timeout=1)
        self.assertEqual(ctx.exception.code, ErrorCode.ENGINE_FAILED)
        self.assertLess(time.monotonic() - began, 15)

    def test_cancel_stops_process(self) -> None:
        cancel = threading.Event()
        threading.Timer(0.8, cancel.set).start()
        began = time.monotonic()
        with self.assertRaises(UpscaleError) as ctx:
            self._run("hang", cancel=cancel)
        self.assertEqual(ctx.exception.code, ErrorCode.CANCELLED)
        self.assertLess(time.monotonic() - began, 15)

    def test_callback_exception_does_not_break_run(self) -> None:
        def boom(_p: float) -> None:
            raise RuntimeError("ui bug")

        with mock.patch.dict(os.environ, {"FAKE_MODE": "ok"}):
            run_engine(FAKE, self.src, self.dst, "m", 4, 0, 0, None, 20, boom, threading.Event())
        self.assertTrue(self.dst.exists())


if __name__ == "__main__":
    unittest.main()
