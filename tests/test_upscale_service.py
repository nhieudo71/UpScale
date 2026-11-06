import os
import queue
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from upscale.domain.models import ErrorCode, EventType, JobEvent, UpscaleError, UpscaleRequest
from upscale.infra.config import Config, load_config
from upscale.services.upscale_service import UpscaleService

FAKE = [sys.executable, str(Path(__file__).with_name("fake_engine.py"))]
TERMINAL = {EventType.DONE, EventType.FAILED}


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.src = self.dir / "cat.png"
        Image.new("RGB", (10, 8), (10, 200, 10)).save(self.src)

    def _service(self, **cfg: int) -> UpscaleService:
        svc = UpscaleService(Config(project_root=self.dir, **cfg), engine_cmd=FAKE)
        self.addCleanup(svc.shutdown)
        return svc

    def _run(self, svc: UpscaleService, req: UpscaleRequest, mode: str = "ok") -> list[JobEvent]:
        q: queue.Queue[JobEvent] = queue.Queue()
        with mock.patch.dict(os.environ, {"FAKE_MODE": mode}):
            svc.start(req, q.put)
            events: list[JobEvent] = []
            while True:
                event = q.get(timeout=30)
                events.append(event)
                if event.type in TERMINAL:
                    return events

    def test_success_event_order_and_output(self) -> None:
        events = self._run(self._service(), UpscaleRequest(str(self.src), scale=4))
        types = [e.type for e in events]
        self.assertEqual(types[0], EventType.STARTED)
        self.assertEqual(types[-1], EventType.DONE)
        self.assertEqual(types.count(EventType.DONE) + types.count(EventType.FAILED), 1)
        done = events[-1]
        self.assertEqual((done.output_w, done.output_h), (40, 32))
        self.assertEqual(Path(done.output_path or "").name, "cat_x4.png")
        with Image.open(done.output_path or "") as img:
            self.assertEqual(img.size, (40, 32))
        self.assertEqual(sorted(os.listdir(self.dir)), ["cat.png", "cat_x4.png"])

    def test_never_overwrites_existing_output(self) -> None:
        existing = self.dir / "cat_x4.png"
        existing.write_bytes(b"du lieu cua nguoi dung")
        done = self._run(self._service(), UpscaleRequest(str(self.src), scale=4))[-1]
        self.assertEqual(Path(done.output_path or "").name, "cat_x4_2.png")
        self.assertEqual(existing.read_bytes(), b"du lieu cua nguoi dung")

    def test_unreadable_image(self) -> None:
        bad = self.dir / "bad.png"
        bad.write_bytes(b"khong phai anh")
        last = self._run(self._service(), UpscaleRequest(str(bad)))[-1]
        self.assertEqual((last.type, last.code), (EventType.FAILED, ErrorCode.IMAGE_UNREADABLE))

    def test_missing_file(self) -> None:
        last = self._run(self._service(), UpscaleRequest(str(self.dir / "khong-co.png")))[-1]
        self.assertEqual(last.code, ErrorCode.IMAGE_UNREADABLE)

    def test_output_too_large_blocks_before_engine(self) -> None:
        last = self._run(self._service(max_output_pixels=100), UpscaleRequest(str(self.src), scale=4))[-1]
        self.assertEqual(last.code, ErrorCode.OUTPUT_TOO_LARGE)
        self.assertEqual(os.listdir(self.dir), ["cat.png"])

    def test_wrong_output_size_is_rejected_and_cleaned(self) -> None:
        last = self._run(self._service(), UpscaleRequest(str(self.src), scale=4), mode="wrongsize")[-1]
        self.assertEqual(last.code, ErrorCode.ENGINE_FAILED)
        self.assertEqual(os.listdir(self.dir), ["cat.png"])

    def test_engine_failure_cleans_tmp(self) -> None:
        last = self._run(self._service(), UpscaleRequest(str(self.src)), mode="oom")[-1]
        self.assertEqual(last.code, ErrorCode.OUT_OF_VRAM)
        self.assertEqual(os.listdir(self.dir), ["cat.png"])

    def test_engine_missing_with_real_paths(self) -> None:
        svc = UpscaleService(Config(project_root=self.dir))  # không có engine\ trong thư mục tạm
        last = self._run(svc, UpscaleRequest(str(self.src)))[-1]
        self.assertEqual(last.code, ErrorCode.ENGINE_MISSING)
        self.assertIn("realesrgan-ncnn-vulkan.exe", last.message or "")

    def test_cancel_and_busy_then_reusable(self) -> None:
        svc = self._service()
        q: queue.Queue[JobEvent] = queue.Queue()
        with mock.patch.dict(os.environ, {"FAKE_MODE": "hang"}):
            job_id = svc.start(UpscaleRequest(str(self.src)), q.put)
            with self.assertRaises(UpscaleError) as ctx:
                svc.start(UpscaleRequest(str(self.src)), q.put)
            self.assertEqual(ctx.exception.code, ErrorCode.BUSY)
            svc.cancel(job_id)
            while True:
                event = q.get(timeout=30)
                if event.type in TERMINAL:
                    break
        self.assertEqual(event.code, ErrorCode.CANCELLED)
        svc.shutdown()  # chờ luồng job kết thúc hẳn (đã hủy nên trả về ngay)
        self.assertEqual(os.listdir(self.dir), ["cat.png"])
        self.assertEqual(self._run(svc, UpscaleRequest(str(self.src)))[-1].type, EventType.DONE)

    def test_callback_exception_does_not_break_job(self) -> None:
        svc = self._service()
        with mock.patch.dict(os.environ, {"FAKE_MODE": "ok"}):
            svc.start(UpscaleRequest(str(self.src)), mock.Mock(side_effect=RuntimeError("ui bug")))
            svc._thread.join(timeout=30)  # type: ignore[union-attr]
        self.assertTrue((self.dir / "cat_x4.png").exists())


class ConfigTests(unittest.TestCase):
    def test_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = load_config(project_root=Path(d))
        self.assertEqual((cfg.gpu_id, cfg.tile, cfg.max_output_pixels, cfg.engine_timeout_s), (0, 0, 0, 600))

    def test_valid_and_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "config.toml").write_text(
                'gpu_id = 1\ntile = "abc"\nmax_output_pixels = -5\nengine_timeout_s = 30\n', encoding="utf-8"
            )
            cfg = load_config(project_root=root)
        self.assertEqual((cfg.gpu_id, cfg.tile, cfg.max_output_pixels, cfg.engine_timeout_s), (1, 0, 0, 30))

    def test_broken_toml_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "config.toml").write_text("gpu_id = [", encoding="utf-8")
            self.assertEqual(load_config(project_root=root).gpu_id, 0)


if __name__ == "__main__":
    unittest.main()

