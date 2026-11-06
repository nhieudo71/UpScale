import unittest

from upscale.domain.models import ErrorCode, ImageInfo
from upscale.ui.event_bridge import EventBridge
from upscale.ui.presenter import (
    Action, NoticeKind, describe_scale, done_notice, ellipsize_middle, format_duration, notice_for_error,
)
from upscale.ui.theme import TOKENS, contrast_ratio, points_to_ctk_size
from upscale.ui.views import is_edit_key


class PresenterTests(unittest.TestCase):
    def test_every_error_code_has_a_notice_and_never_empty(self) -> None:
        for code in ErrorCode:
            notice = notice_for_error(code, None, 4)
            self.assertTrue(notice.title and notice.body, code)

    def test_cancelled_is_info_not_error(self) -> None:
        self.assertEqual(notice_for_error(ErrorCode.CANCELLED, None, 4).kind, NoticeKind.INFO)

    def test_too_large_offers_2x_only_when_scale_is_4(self) -> None:
        self.assertIn(Action.SET_2X, notice_for_error(ErrorCode.OUTPUT_TOO_LARGE, "x", 4).actions)
        self.assertNotIn(Action.SET_2X, notice_for_error(ErrorCode.OUTPUT_TOO_LARGE, "x", 2).actions)

    def test_service_message_is_kept(self) -> None:
        self.assertEqual(notice_for_error(ErrorCode.ENGINE_FAILED, "chi tiet", 4).body, "chi tiet")

    def test_describe_scale(self) -> None:
        self.assertEqual(describe_scale(ImageInfo("a.png", 220, 220, "PNG"), 4), "220 x 220 thành 880 x 880")

    def test_ellipsize_middle(self) -> None:
        self.assertEqual(ellipsize_middle("abc", 10), "abc")
        out = ellipsize_middle("C:\\Users\\Admin\\Pictures\\anh-rat-dai.png", 20)
        self.assertEqual(len(out), 20)
        self.assertTrue(out.startswith("C:\\Users") and out.endswith("dai.png") and "..." in out)

    def test_format_duration(self) -> None:
        self.assertEqual(format_duration(5547), "5,5 giây")
        self.assertEqual(format_duration(125_000), "2 phút 5 giây")
        self.assertEqual(format_duration(-5), "0,0 giây")

    def test_done_notice_mentions_rename_only_when_renamed(self) -> None:
        plain = done_notice("D:\\a\\cat.png", "D:\\a\\cat_x4.png", 4, 40, 32, 1000)
        renamed = done_notice("D:\\a\\cat.png", "D:\\a\\cat_x4_2.png", 4, 40, 32, 1000)
        self.assertNotIn("cùng tên", plain.body)
        self.assertIn("cat_x4_2.png", renamed.body)
        self.assertEqual(plain.kind, NoticeKind.SUCCESS)


class ThemeTests(unittest.TestCase):
    def ratio(self, fg: str, bg: str, dark: bool) -> float:
        return contrast_ratio(TOKENS[fg][1 if dark else 0], TOKENS[bg][1 if dark else 0])

    def test_matches_spec_table_values(self) -> None:
        # Giá trị trong docs/UX-UI-SPEC.md mục 2.1 (sáng, tối).
        for fg, bg, light, dark in [
            ("text", "bg", 16.24, 16.38), ("on-primary", "primary", 7.90, 4.88),
            ("danger", "surface", 6.57, 7.70), ("border", "bg", 3.56, 4.00),
        ]:
            self.assertAlmostEqual(self.ratio(fg, bg, False), light, delta=0.02, msg=f"{fg}/{bg} sáng")
            self.assertAlmostEqual(self.ratio(fg, bg, True), dark, delta=0.02, msg=f"{fg}/{bg} tối")

    def test_text_pairs_reach_4_5(self) -> None:
        pairs = [("text", "bg"), ("text", "surface"), ("text", "surface-alt"), ("text-muted", "surface-alt"),
                 ("on-primary", "primary"), ("on-primary", "primary-hover"), ("on-danger", "danger"),
                 ("danger", "danger-bg"), ("success", "success-bg"), ("secondary", "secondary-bg"),
                 ("warning", "warning-bg"),
                 # Token không có trong spec: kiểm riêng.
                 ("text", "secondary-hover"), ("on-danger", "danger-hover")]
        for dark in (False, True):
            for fg, bg in pairs:
                self.assertGreaterEqual(self.ratio(fg, bg, dark), 4.5, f"{fg}/{bg} dark={dark}")

    def test_border_reaches_3_on_surfaces(self) -> None:
        for dark in (False, True):
            for bg in ("bg", "surface", "surface-alt"):
                self.assertGreaterEqual(self.ratio("border", bg, dark), 3.0, f"border/{bg} dark={dark}")

    def test_points_to_pixels(self) -> None:
        self.assertEqual([points_to_ctk_size(p) for p in (10, 11, 14, 20)], [13, 15, 19, 27])


class FakeScheduler:
    def __init__(self) -> None:
        self.pending: list[tuple[str, object]] = []
        self.cancelled: list[str] = []
        self._n = 0

    def after(self, ms: int, func: object) -> str:
        self._n += 1
        self.pending.append((f"id{self._n}", func))
        return f"id{self._n}"

    def after_cancel(self, id: str) -> None:
        self.cancelled.append(id)
        self.pending = [p for p in self.pending if p[0] != id]

    def run_next(self) -> None:
        _, func = self.pending.pop(0)
        func()  # type: ignore[operator]


class EventBridgeTests(unittest.TestCase):
    def test_delivers_in_order_and_reschedules(self) -> None:
        sched, got = FakeScheduler(), []
        bridge = EventBridge(sched, got.append)
        bridge.start()
        for i in range(3):
            bridge.push(i)
        sched.run_next()
        self.assertEqual(got, [0, 1, 2])
        self.assertEqual(len(sched.pending), 1)

    def test_handler_exception_does_not_stop_loop(self) -> None:
        sched, got = FakeScheduler(), []

        def handler(item: int) -> None:
            if item == 1:
                raise RuntimeError("boom")
            got.append(item)

        bridge = EventBridge(sched, handler)
        bridge.start()
        for i in range(3):
            bridge.push(i)
        with self.assertLogs("upscale.ui.event_bridge", level="ERROR"):
            sched.run_next()
        self.assertEqual(got, [0, 2])
        self.assertEqual(len(sched.pending), 1)

    def test_max_per_tick_limits_batch(self) -> None:
        sched, got = FakeScheduler(), []
        bridge = EventBridge(sched, got.append, max_per_tick=2)
        bridge.start()
        for i in range(5):
            bridge.push(i)
        sched.run_next()
        self.assertEqual(got, [0, 1])
        sched.run_next()
        self.assertEqual(got, [0, 1, 2, 3])

    def test_close_cancels_drops_queue_and_ignores_push(self) -> None:
        sched, got = FakeScheduler(), []
        bridge = EventBridge(sched, got.append)
        bridge.start()
        bridge.push(1)
        bridge.close()
        bridge.push(2)
        self.assertEqual(sched.cancelled, ["id1"])
        self.assertEqual(sched.pending, [])
        self.assertEqual(got, [])


class KeyFilterTests(unittest.TestCase):
    def test_readonly_field_key_rules(self) -> None:
        self.assertTrue(is_edit_key("a", "a", False))
        self.assertTrue(is_edit_key("BackSpace", "\x08", False))
        self.assertTrue(is_edit_key("v", "\x16", True))
        for keysym, char, ctrl in [("Tab", "\t", False), ("Left", "", False), ("c", "\x03", True),
                                   ("a", "\x01", True), ("o", "\x0f", True), ("Escape", "\x1b", False)]:
            self.assertFalse(is_edit_key(keysym, char, ctrl), keysym)


if __name__ == "__main__":
    unittest.main()
