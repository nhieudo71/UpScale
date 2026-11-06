"""Test tích hợp giao diện: cửa sổ Tk thật, engine giả, hộp thoại chọn file giả. Cần màn hình desktop."""
import os
import sys
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from PIL import Image

from upscale.infra.config import Config
from upscale.services.upscale_service import UpscaleService
from upscale.ui.app import App, State
from upscale.ui.presenter import NoticeKind

FAKE = [sys.executable, str(Path(__file__).with_name("fake_engine.py"))]


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.src = self.dir / "cat.png"
        Image.new("RGB", (10, 8), (10, 200, 10)).save(self.src)
        self.choice = str(self.src)
        self.opened: list[Path] = []
        # Gốc dự án giả có đủ file engine rỗng để không rơi vào M1. Engine thật không cần có
        # (CI không có GPU), vì UpscaleService luôn chạy engine giả FAKE.
        self._root_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._root_tmp.cleanup)
        self.root = Path(self._root_tmp.name)
        probe = Config(project_root=self.root)
        probe.models_dir.mkdir(parents=True)
        for stub in (
            probe.engine_exe,
            probe.models_dir / "realesrgan-x4plus.param",
            probe.models_dir / "realesrgan-x4plus.bin",
        ):
            stub.touch()

    def make_app(self, config: Config | None = None) -> App:
        config = config or Config(project_root=self.root)
        service = UpscaleService(config, engine_cmd=FAKE)
        app = App(config, service, ask_open_file=lambda: self.choice, open_path=self.opened.append)
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

    def test_happy_path_s0_to_s3_and_back(self) -> None:
        with mock.patch.dict(os.environ, {"FAKE_MODE": "ok"}):
            app = self.make_app()
            self.assertEqual(app._state, State.S0)
            self.assertTrue(self.shown(app._pick_button))
            self.assertFalse(self.shown(app._upscale_button))
            app._pick()
            app.update()
            self.assertEqual(app._state, State.S1)
            self.assertEqual(app._name_label.cget("text"), "cat.png")
            self.assertEqual(app._dims_label.cget("text"), "10 x 8 thành 40 x 32")
            app._scale_seg._select("2")
            self.assertEqual(app._dims_label.cget("text"), "10 x 8 thành 20 x 16")
            app._scale_seg._select("4")
            app._start()
            self.pump(app, lambda: app._state in (State.S3, State.S1))
            self.assertEqual(app._state, State.S3)
            self.assertTrue((self.dir / "cat_x4.png").exists())
            self.assertEqual(app._result_path.full_text, str(self.dir / "cat_x4.png"))
            self.assertEqual(app._notice_card.notice.kind, NoticeKind.SUCCESS)
            app._open_folder()
            self.assertEqual(self.opened, [self.dir])
            app._reset_to_s0()
            self.assertEqual(app._state, State.S0)
            self.assertIsNone(app._notice_card)

    def test_controls_locked_while_processing_then_cancel(self) -> None:
        with mock.patch.dict(os.environ, {"FAKE_MODE": "hang"}):
            app = self.make_app()
            app._pick()
            app._start()
            # Kiểm tra trước khi vòng lặp Tk chạy: engine giả in 0% ngay, nên sau update() thanh tiến độ
            # có thể đã chuyển sang chế độ xác định và phép kiểm tra này sẽ phụ thuộc thời gian.
            self.assertTrue(app._progress.indeterminate)
            app.update()
            self.assertEqual(app._state, State.S2)
            self.assertFalse(app._upscale_button.enabled)
            self.assertFalse(app._pick_button.enabled)
            self.assertEqual(app._upscale_button.cget("text"), "Đang xử lý...")
            app._ask_cancel()
            app.update()
            self.assertIsNotNone(app._dialog)
            app._ask_cancel()  # lần hai không mở thêm hộp thoại
            app._dialog.confirm_button.invoke()
            self.pump(app, lambda: app._state is State.S1)
            self.assertIsNone(app._dialog)
            self.assertEqual(app._notice_card.notice.kind, NoticeKind.INFO)
            self.assertEqual(sorted(os.listdir(self.dir)), ["cat.png"])
            self.assertTrue(app._upscale_button.enabled)

    def test_keep_processing_closes_dialog_only(self) -> None:
        with mock.patch.dict(os.environ, {"FAKE_MODE": "ok", "FAKE_DELAY": "1.5"}):
            app = self.make_app()
            app._pick()
            app._start()
            app.update()
            app._ask_cancel()
            app.update()
            app._dialog.keep_button.invoke()
            self.assertIsNone(app._dialog)
            self.assertEqual(app._state, State.S2)
            self.pump(app, lambda: app._state is not State.S2)
            self.assertEqual(app._state, State.S3)

    def test_engine_failure_returns_to_s1_with_retry(self) -> None:
        with mock.patch.dict(os.environ, {"FAKE_MODE": "fail"}):
            app = self.make_app()
            app._pick()
            app._start()
            self.pump(app, lambda: app._state is not State.S2)
            self.assertEqual(app._state, State.S1)
            self.assertEqual(app._notice_card.notice.kind, NoticeKind.ERROR)
            self.assertIn("retry", [a.value for a in app._notice_card.notice.actions])
            self.assertEqual(sorted(os.listdir(self.dir)), ["cat.png"])

    def test_unreadable_image_goes_to_s0_and_app_still_works(self) -> None:
        bad = self.dir / "bad.png"
        bad.write_bytes(b"khong phai anh")
        with mock.patch.dict(os.environ, {"FAKE_MODE": "ok"}):
            app = self.make_app()
            self.choice = str(bad)
            app._pick()
            self.assertEqual(app._state, State.S0)
            self.assertEqual(app._notice_card.notice.title, "Không đọc được ảnh")
            self.choice = str(self.src)
            app._pick()
            self.assertEqual(app._state, State.S1)
            self.assertIsNone(app._notice_card)

    def test_output_limit_blocks_before_running(self) -> None:
        config = Config(project_root=self.root, max_output_pixels=100)
        app = self.make_app(config)
        app.geometry("760x560")
        app._pick()
        app._start()
        self.assertEqual(app._state, State.S1)
        self.assertEqual(app._notice_card.notice.title, "Ảnh kết quả quá lớn")
        self.assert_fits(app, "S1 kèm thẻ lỗi 2 dòng có nút 2x")
        self.assertIn("set_2x", [a.value for a in app._notice_card.notice.actions])
        app._notice_card.buttons[app._notice_card.notice.actions[0]].invoke()
        app.update()
        self.assertEqual(app._scale(), 2)

    def test_missing_engine_shows_m1_and_hides_card(self) -> None:
        app = self.make_app(Config(project_root=self.dir))
        self.assertEqual(app._state, State.M1)
        self.assertFalse(self.shown(app._card))
        self.assertIn("Thiếu engine", app._notice_card.notice.title)
        app._pick()  # M1 không cho chọn ảnh
        self.assertEqual(app._state, State.M1)

    def test_escape_outside_processing_does_nothing(self) -> None:
        app = self.make_app()
        app._ask_cancel()
        self.assertIsNone(app._dialog)

    def assert_fits(self, app: App, label: str) -> None:
        """Mọi widget đang hiện phải nằm trọn trong cửa sổ, nếu không đáy (nút Upscale, tiến độ) bị cắt."""
        app.update()
        window_bottom = app.winfo_rooty() + app.winfo_height()
        stack, lowest = list(app.winfo_children()), 0
        while stack:
            widget = stack.pop()
            if widget.winfo_toplevel() is not app:
                continue  # hộp thoại là cửa sổ riêng
            stack.extend(widget.winfo_children())
            if widget.winfo_ismapped():
                lowest = max(lowest, widget.winfo_rooty() + widget.winfo_height())
        self.assertLessEqual(lowest, window_bottom, f"{label}: nội dung tràn đáy {lowest - window_bottom}px")

    def test_every_state_fits_in_minimum_window(self) -> None:
        with mock.patch.dict(os.environ, {"FAKE_MODE": "hang"}):
            app = self.make_app()
            app.geometry("760x560")  # window-min của spec; CTk tự nhân hệ số DPI
            self.assert_fits(app, "S0")
            app._pick()
            self.assert_fits(app, "S1")
            app._start()
            self.assert_fits(app, "S2")

    def test_worst_case_states_fit_in_minimum_window(self) -> None:
        with mock.patch.dict(os.environ, {"FAKE_MODE": "fail"}):
            app = self.make_app()
            app.geometry("760x560")
            app._pick()
            app._start()
            self.pump(app, lambda: app._state is State.S1)
            self.assert_fits(app, "S1 kèm thẻ lỗi có 2 nút")
        with mock.patch.dict(os.environ, {"FAKE_MODE": "ok"}):
            app._start()
            self.pump(app, lambda: app._state is State.S3)
            self.assert_fits(app, "S3")


    @staticmethod
    def press(widget: object, sequence: str) -> None:
        """Gửi phím tới widget. Tk chuyển phím tới widget đang giữ focus, nên phải đặt focus trước."""
        widget.focus_force()  # type: ignore[attr-defined]
        widget.update()  # type: ignore[attr-defined]
        widget.event_generate(sequence)  # type: ignore[attr-defined]
        widget.update()  # type: ignore[attr-defined]

    def test_keyboard_operation(self) -> None:
        """Phím thật (event_generate) thay vì invoke(): Ctrl+O, Enter/Space, mũi tên, Esc (US-02)."""
        picks: list[int] = []
        with mock.patch.dict(os.environ, {"FAKE_MODE": "hang"}):
            app = self.make_app()
            app._ask_open_file = lambda: (picks.append(1), str(self.src))[1]
            self.press(app, "<Control-o>")
            self.assertEqual((app._state, len(picks)), (State.S1, 1))
            self.press(app._pick_button._canvas, "<Return>")
            self.assertEqual(len(picks), 2)
            self.press(app._scale_seg._buttons["4"]._canvas, "<Left>")
            self.assertEqual(app._scale(), 2)
            self.press(app._scale_seg._buttons["2"]._canvas, "<Right>")
            self.assertEqual(app._scale(), 4)
            self.press(app._upscale_button._canvas, "<space>")
            self.assertEqual(app._state, State.S2)
            self.press(app, "<Escape>")
            self.assertIsNotNone(app._dialog)
            # CTkToplevel hiện trễ và grab_set chạy sau 100 ms, nên chờ tới khi focus nằm trong hộp thoại.
            dialog = app._dialog
            self.pump(app, lambda: bool(dialog.winfo_viewable()) and str(app.focus_get()).startswith(str(dialog)))
            self.assertIs(app.focus_get(), dialog.keep_button._canvas)  # spec 3.5: focus đầu ở nút an toàn
            app.focus_get().event_generate("<Escape>")  # phím thật đến widget có focus rồi nổi lên toplevel
            app.update()
            self.assertIsNone(app._dialog)
            self.assertEqual(app._state, State.S2)  # Esc chỉ đóng hộp thoại, job vẫn chạy


if __name__ == "__main__":
    unittest.main()
