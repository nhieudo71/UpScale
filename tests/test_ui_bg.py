"""Giao diện ở chế độ Xóa nền: cửa sổ Tk thật, engine upscale giả, model xóa nền giả. Cần màn hình desktop."""
import os
import sys
import tempfile
import threading
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from PIL import Image

from tests.test_bgremoval import left_half_predictor
from upscale.bgremoval.service import BackgroundRemovalService
from upscale.domain.models import ErrorCode, UpscaleError
from upscale.infra.config import Config
from upscale.services.upscale_service import UpscaleService
from upscale.ui.app import App, State
from upscale.ui.presenter import NoticeKind

FAKE = [sys.executable, str(Path(__file__).with_name("fake_engine.py"))]


class BgAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.src = self.dir / "cat.png"
        Image.new("RGB", (10, 8), (10, 200, 10)).save(self.src)
        # Gốc dự án giả có đủ file engine rỗng để không rơi vào M1.
        self._root_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._root_tmp.cleanup)
        self.root = Path(self._root_tmp.name)
        self.config = Config(project_root=self.root)
        self.config.models_dir.mkdir(parents=True)
        for stub in (
            self.config.engine_exe,
            self.config.models_dir / "realesrgan-x4plus.param",
            self.config.models_dir / "realesrgan-x4plus.bin",
        ):
            stub.touch()

    def make_app(self, loader: Callable[[Path], object] | None = None) -> App:
        service = UpscaleService(self.config, engine_cmd=FAKE)
        bg = BackgroundRemovalService(self.config, loader or (lambda _p: left_half_predictor))
        app = App(self.config, service, ask_open_file=lambda: str(self.src), open_path=lambda _p: None, bg_service=bg)
        self.addCleanup(self._close, app)
        app.update()
        return app

    @staticmethod
    def _close(app: App) -> None:
        try:
            app._on_close()
        except Exception:  # cửa sổ có thể đã bị hủy trong test
            pass

    @staticmethod
    def pump(app: App, until: Callable[[], bool], timeout: float = 20.0) -> None:
        end = time.monotonic() + timeout
        while not until():
            if time.monotonic() > end:
                raise AssertionError("hết thời gian chờ giao diện")
            app.update()
            time.sleep(0.01)

    @staticmethod
    def shown(widget: object) -> bool:
        return bool(widget.winfo_ismapped())  # type: ignore[attr-defined]

    def test_mode_switch_hides_options_and_relabels_button(self) -> None:
        app = self.make_app()
        app._pick()
        app.update()
        self.assertTrue(self.shown(app._scale_seg))
        self.assertEqual(app._upscale_button.cget("text"), "Upscale")
        app._mode_seg._select("bg")
        app.update()
        self.assertFalse(self.shown(app._scale_seg))
        self.assertFalse(self.shown(app._model_seg))
        self.assertEqual(app._upscale_button.cget("text"), "Xóa nền")
        self.assertEqual(app._dims_label.cget("text"), "10 x 8")
        app._mode_seg._select("upscale")
        app.update()
        self.assertTrue(self.shown(app._scale_seg))
        self.assertEqual(app._upscale_button.cget("text"), "Upscale")

    def test_hint_follows_mode_on_first_screen(self) -> None:
        app = self.make_app()
        app._mode_seg._select("bg")
        app.update()
        self.assertIn("xóa nền", app._sections["hint"].cget("text"))
        self.assertEqual(app._state, State.S0)

    def test_remove_background_end_to_end(self) -> None:
        app = self.make_app()
        app._pick()
        app._mode_seg._select("bg")
        app._start()
        self.pump(app, lambda: app._state in (State.S3, State.S1))
        self.assertEqual(app._state, State.S3)
        out = self.dir / "cat_nobg.png"
        self.assertEqual(app._result_path.full_text, str(out))
        self.assertEqual(app._notice_card.notice.kind, NoticeKind.SUCCESS)
        self.assertIn("không nền", app._notice_card.notice.title)
        with Image.open(out) as result:
            self.assertEqual((result.mode, result.size), ("RGBA", (10, 8)))
        self.assertEqual(sorted(os.listdir(self.dir)), ["cat.png", "cat_nobg.png"])
        self.assertFalse((self.dir / "cat_x4.png").exists())  # không chạy nhầm upscale

    def test_upscale_still_works_after_using_background_mode(self) -> None:
        app = self.make_app()
        app._pick()
        app._mode_seg._select("bg")
        app._start()
        self.pump(app, lambda: app._state is not State.S2)
        app._reset_to_s0()
        app._pick()
        app._mode_seg._select("upscale")
        with mock.patch.dict(os.environ, {"FAKE_MODE": "ok"}):
            app._start()
            self.pump(app, lambda: app._state is not State.S2)
        self.assertEqual(app._state, State.S3)
        self.assertTrue((self.dir / "cat_x4.png").exists())

    def test_missing_model_shows_error_without_2x_suggestion(self) -> None:
        def loader(_path: Path):
            raise UpscaleError(ErrorCode.ENGINE_MISSING, "Không tìm thấy model xóa nền: x")

        app = self.make_app(loader)
        app._pick()
        app._mode_seg._select("bg")
        app._start()
        self.pump(app, lambda: app._state is not State.S2)
        self.assertEqual(app._state, State.S1)
        self.assertEqual(app._notice_card.notice.kind, NoticeKind.ERROR)
        self.assertNotIn("set_2x", [a.value for a in app._notice_card.notice.actions])
        self.assertEqual(os.listdir(self.dir), ["cat.png"])

    def test_mode_locked_while_processing_then_cancel(self) -> None:
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def slow_loader(_path: Path):
            entered.set()
            release.wait(10)
            return left_half_predictor

        app = self.make_app(slow_loader)
        app._pick()
        app._mode_seg._select("bg")
        app._start()
        app.update()
        self.assertEqual(app._state, State.S2)
        self.assertFalse(app._mode_seg._enabled)
        self.assertTrue(entered.wait(10))
        app._ask_cancel()
        app.update()
        app._dialog.confirm_button.invoke()
        release.set()
        self.pump(app, lambda: app._state is State.S1)
        self.assertEqual(app._notice_card.notice.kind, NoticeKind.INFO)
        self.assertTrue(app._mode_seg._enabled)
        self.assertEqual(os.listdir(self.dir), ["cat.png"])


if __name__ == "__main__":
    unittest.main()
