import os
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

from upscale.bgremoval import matting
from upscale.bgremoval.rules import output_candidates
from upscale.bgremoval.service import BackgroundRemovalService
from upscale.bgremoval.session import MODEL_SHA256, load_onnx_predictor, model_path
from upscale.domain.models import ErrorCode, EventType, JobEvent, UpscaleError
from upscale.infra.config import Config

TERMINAL = {EventType.DONE, EventType.FAILED}


def left_half_predictor(batch: np.ndarray) -> np.ndarray:
    """Model giả: giữ nửa trái (1.0), xóa nửa phải (0.0). Hình đầu ra giống model thật (1, 1, 320, 320)."""
    out = np.zeros((1, 1, matting.INPUT_SIZE, matting.INPUT_SIZE), dtype=np.float32)
    out[..., : matting.INPUT_SIZE // 2] = 1.0
    return out


class MattingTests(unittest.TestCase):
    def test_preprocess_shape_dtype_and_normalisation(self) -> None:
        batch = matting.preprocess(Image.new("RGB", (50, 30), (255, 255, 255)))
        self.assertEqual(batch.shape, (1, 3, 320, 320))
        self.assertEqual(batch.dtype, np.float32)
        self.assertAlmostEqual(float(batch[0, 0, 0, 0]), (1 - 0.485) / 0.229, places=4)
        self.assertAlmostEqual(float(batch[0, 2, 5, 5]), (1 - 0.406) / 0.225, places=4)

    def test_preprocess_black_image_is_finite(self) -> None:
        batch = matting.preprocess(Image.new("RGB", (8, 8), (0, 0, 0)))
        self.assertTrue(np.isfinite(batch).all())

    def test_preprocess_accepts_palette_and_alpha_modes(self) -> None:
        for mode in ("L", "P", "RGBA", "LA"):
            self.assertEqual(matting.preprocess(Image.new(mode, (5, 5))).shape, (1, 3, 320, 320), mode)

    def test_mask_is_rescaled_to_image_size_and_stretched_to_full_range(self) -> None:
        mask = matting.mask_from_prediction(left_half_predictor(np.zeros(1)), (64, 40))
        self.assertEqual((mask.mode, mask.size), ("L", (64, 40)))
        self.assertEqual(mask.getpixel((2, 20)), 255)
        self.assertEqual(mask.getpixel((61, 20)), 0)

    def test_mask_from_flat_prediction_does_not_divide_by_zero(self) -> None:
        mask = matting.mask_from_prediction(np.full((1, 1, 320, 320), 0.5, dtype=np.float32), (10, 10))
        self.assertEqual(mask.getextrema(), (0, 0))

    def test_mask_rejects_unexpected_shape(self) -> None:
        with self.assertRaises(ValueError):
            matting.mask_from_prediction(np.zeros((1, 3, 320, 320), dtype=np.float32), (10, 10))

    def test_apply_mask_sets_alpha_and_keeps_colour(self) -> None:
        image = Image.new("RGB", (4, 4), (10, 20, 30))
        mask = Image.new("L", (4, 4), 0)
        mask.paste(255, (0, 0, 2, 4))
        result = matting.apply_mask(image, mask)
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.getpixel((0, 0)), (10, 20, 30, 255))
        self.assertEqual(result.getpixel((3, 0))[3], 0)

    def test_apply_mask_keeps_existing_transparency(self) -> None:
        image = Image.new("RGBA", (2, 1), (1, 2, 3, 255))
        image.putpixel((1, 0), (1, 2, 3, 0))
        result = matting.apply_mask(image, Image.new("L", (2, 1), 255))
        self.assertEqual([result.getpixel((x, 0))[3] for x in range(2)], [255, 0])


class RulesTests(unittest.TestCase):
    def test_candidates_never_repeat_and_stay_beside_source(self) -> None:
        names = []
        gen = output_candidates(Path("D:/Anh/cat.jpg"))
        for _ in range(3):
            path = next(gen)
            names.append(path.name)
            self.assertEqual(path.parent, Path("D:/Anh"))
        self.assertEqual(names, ["cat_nobg.png", "cat_nobg_2.png", "cat_nobg_3.png"])


class SessionTests(unittest.TestCase):
    def test_model_path_is_under_engine_background(self) -> None:
        self.assertEqual(model_path(Path("D:/P")), Path("D:/P/engine/background/u2net.onnx"))

    def test_missing_model_is_engine_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d, self.assertRaises(UpscaleError) as ctx:
            load_onnx_predictor(Path(d) / "khong-co.onnx")
        self.assertEqual(ctx.exception.code, ErrorCode.ENGINE_MISSING)

    def test_wrong_hash_is_rejected_before_onnxruntime_parses_it(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / "u2net.onnx"
            fake.write_bytes(b"khong phai model")
            with self.assertRaises(UpscaleError) as ctx:
                load_onnx_predictor(fake)
        self.assertEqual(ctx.exception.code, ErrorCode.ENGINE_FAILED)
        self.assertIn("sha256=", ctx.exception.detail)


REAL_MODEL = model_path(Config().project_root)


@unittest.skipUnless(REAL_MODEL.exists(), "không có engine/background/u2net.onnx (CI không có model)")
class RealModelTests(unittest.TestCase):
    def test_real_model_loads_and_returns_mask_shaped_output(self) -> None:
        import hashlib

        self.assertEqual(hashlib.sha256(REAL_MODEL.read_bytes()).hexdigest(), MODEL_SHA256)
        predict = load_onnx_predictor(REAL_MODEL)
        out = predict(matting.preprocess(Image.new("RGB", (64, 48), (200, 30, 30))))
        self.assertEqual(np.asarray(out).shape, (1, 1, 320, 320))


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.src = self.dir / "cat.png"
        Image.new("RGB", (40, 20), (10, 200, 10)).save(self.src)

    def _service(self, loader=None, **cfg: int) -> BackgroundRemovalService:
        svc = BackgroundRemovalService(Config(project_root=self.dir, **cfg), loader or (lambda _p: left_half_predictor))
        self.addCleanup(svc.shutdown)
        return svc

    @staticmethod
    def _run(svc: BackgroundRemovalService, path: Path) -> list[JobEvent]:
        q: queue.Queue[JobEvent] = queue.Queue()
        svc.start(str(path), q.put)
        events: list[JobEvent] = []
        while True:
            event = q.get(timeout=30)
            events.append(event)
            if event.type in TERMINAL:
                return events

    def test_success_event_order_output_and_alpha(self) -> None:
        events = self._run(self._service(), self.src)
        types = [e.type for e in events]
        self.assertEqual(types[0], EventType.STARTED)
        self.assertEqual(types[-1], EventType.DONE)
        self.assertEqual(sum(t in TERMINAL for t in types), 1)
        percents = [e.percent for e in events if e.type is EventType.PROGRESS]
        self.assertEqual(percents, sorted(percents))
        done = events[-1]
        self.assertEqual(Path(done.output_path), self.dir / "cat_nobg.png")
        self.assertEqual((done.output_w, done.output_h), (40, 20))
        with Image.open(done.output_path) as out:
            self.assertEqual((out.mode, out.size), ("RGBA", (40, 20)))
            self.assertEqual(out.getpixel((2, 10))[3], 255)
            self.assertEqual(out.getpixel((37, 10))[3], 0)
        self.assertEqual(sorted(os.listdir(self.dir)), ["cat.png", "cat_nobg.png"])

    def test_source_is_not_modified(self) -> None:
        before = self.src.read_bytes()
        self._run(self._service(), self.src)
        self.assertEqual(self.src.read_bytes(), before)

    def test_second_run_does_not_overwrite(self) -> None:
        svc = self._service()
        self._run(svc, self.src)
        events = self._run(svc, self.src)
        self.assertEqual(Path(events[-1].output_path).name, "cat_nobg_2.png")
        self.assertEqual(sorted(os.listdir(self.dir)), ["cat.png", "cat_nobg.png", "cat_nobg_2.png"])

    def test_model_is_loaded_once_across_jobs(self) -> None:
        loader = mock.Mock(return_value=left_half_predictor)
        svc = self._service(loader)
        self._run(svc, self.src)
        self._run(svc, self.src)
        loader.assert_called_once_with(model_path(self.dir))

    def test_non_ascii_folder_works(self) -> None:
        folder = self.dir / "Đảng"
        folder.mkdir()
        src = folder / "ảnh.png"
        Image.new("RGB", (8, 8), (1, 2, 3)).save(src)
        self.assertEqual(self._run(self._service(), src)[-1].type, EventType.DONE)
        self.assertEqual(sorted(os.listdir(folder)), ["ảnh.png", "ảnh_nobg.png"])

    def test_alpha_png_keeps_transparent_area(self) -> None:
        src = self.dir / "logo.png"
        image = Image.new("RGBA", (40, 20), (5, 5, 5, 255))
        image.paste((5, 5, 5, 0), (0, 0, 10, 20))
        image.save(src)
        events = self._run(self._service(), src)
        with Image.open(events[-1].output_path) as out:
            self.assertEqual(out.getpixel((3, 10))[3], 0)  # trong suốt sẵn thì vẫn trong suốt
            self.assertEqual(out.getpixel((15, 10))[3], 255)

    def test_unreadable_image(self) -> None:
        bad = self.dir / "bad.png"
        bad.write_bytes(b"khong phai anh")
        last = self._run(self._service(), bad)[-1]
        self.assertEqual((last.type, last.code), (EventType.FAILED, ErrorCode.IMAGE_UNREADABLE))

    def test_output_limit(self) -> None:
        last = self._run(self._service(max_output_pixels=100), self.src)[-1]
        self.assertEqual(last.code, ErrorCode.OUTPUT_TOO_LARGE)
        self.assertEqual(os.listdir(self.dir), ["cat.png"])

    def test_model_missing_is_reported(self) -> None:
        def loader(_path: Path):
            raise UpscaleError(ErrorCode.ENGINE_MISSING, "thiếu model")

        last = self._run(self._service(loader), self.src)[-1]
        self.assertEqual((last.code, last.message), (ErrorCode.ENGINE_MISSING, "thiếu model"))

    def test_missing_onnxruntime_is_reported_with_install_hint(self) -> None:
        def loader(_path: Path):
            raise ImportError("No module named 'onnxruntime'")

        last = self._run(self._service(loader), self.src)[-1]
        self.assertEqual(last.code, ErrorCode.ENGINE_MISSING)
        self.assertIn("requirements.txt", last.message)

    def test_model_exception_leaves_no_files_behind(self) -> None:
        def broken(_batch):
            raise RuntimeError("onnx boom")

        last = self._run(self._service(lambda _p: broken), self.src)[-1]
        self.assertEqual((last.type, last.code), (EventType.FAILED, ErrorCode.ENGINE_FAILED))
        self.assertNotIn("boom", last.message)  # chi tiết kỹ thuật chỉ vào log
        self.assertEqual(os.listdir(self.dir), ["cat.png"])

    def test_cancel_while_model_loading(self) -> None:
        entered, release = threading.Event(), threading.Event()

        def slow_loader(_path: Path):
            entered.set()
            release.wait(10)
            return left_half_predictor

        svc = self._service(slow_loader)
        q: queue.Queue[JobEvent] = queue.Queue()
        job_id = svc.start(str(self.src), q.put)
        self.assertTrue(entered.wait(10))
        svc.cancel(job_id)
        release.set()
        events = []
        while not events or events[-1].type not in TERMINAL:
            events.append(q.get(timeout=30))
        self.assertEqual(events[-1].code, ErrorCode.CANCELLED)
        self.assertEqual(os.listdir(self.dir), ["cat.png"])

    def test_busy_while_job_running(self) -> None:
        entered, release = threading.Event(), threading.Event()

        def slow_loader(_path: Path):
            entered.set()
            release.wait(10)
            return left_half_predictor

        svc = self._service(slow_loader)
        q: queue.Queue[JobEvent] = queue.Queue()
        svc.start(str(self.src), q.put)
        self.assertTrue(entered.wait(10))
        with self.assertRaises(UpscaleError) as ctx:
            svc.start(str(self.src), q.put)
        self.assertEqual(ctx.exception.code, ErrorCode.BUSY)
        release.set()

    def test_callback_exception_does_not_break_job(self) -> None:
        svc = self._service()
        done = threading.Event()

        def bad_callback(event: JobEvent) -> None:
            if event.type in TERMINAL:
                done.set()
            raise RuntimeError("ui bug")

        svc.start(str(self.src), bad_callback)
        self.assertTrue(done.wait(30))
        svc.shutdown()
        self.assertTrue((self.dir / "cat_nobg.png").exists())


if __name__ == "__main__":
    unittest.main()
