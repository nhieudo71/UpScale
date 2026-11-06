"""Thành phần giao diện dùng chung: ô đường dẫn chỉ đọc, thẻ thông báo, hàng tiến độ, hộp thoại hủy."""
from __future__ import annotations

import tkinter
from collections.abc import Callable

import customtkinter as ctk

from .presenter import ACTION_LABELS, Action, Notice, NoticeKind, ellipsize_middle
from .theme import CONTROL_HEIGHT, RADIUS_LG, RADIUS_SM, SPACE, color, font
from .widgets import AppButton

_NAV_KEYS = {"Left", "Right", "Up", "Down", "Home", "End", "Tab", "ISO_Left_Tab", "Escape", "Return"}


def is_edit_key(keysym: str, char: str, ctrl: bool) -> bool:
    """True nếu phím làm thay đổi nội dung ô nhập (gõ, xóa, dán, cắt). Ctrl+C, Ctrl+A và phím điều hướng thì không."""
    if keysym in _NAV_KEYS:
        return False
    if keysym in ("BackSpace", "Delete"):
        return True
    if ctrl:
        return keysym.lower() in ("v", "x")
    return bool(char) and char.isprintable()


class PathField(ctk.CTkEntry):
    """Ô đường dẫn chỉ đọc nhưng vẫn bôi chọn và sao chép được. Cắt giữa khi dài, hiện đủ khi rê chuột."""

    def __init__(self, master: ctk.CTkBaseClass, max_chars: int = 60) -> None:
        super().__init__(
            master,
            height=CONTROL_HEIGHT,
            corner_radius=RADIUS_SM,
            border_width=1,
            border_color=color("border"),
            fg_color=color("surface-alt"),
            text_color=color("text"),
            font=font("mono"),
        )
        self._full = ""
        self._max_chars = max_chars
        self.bind("<Key>", self._on_key)
        self.bind("<Enter>", lambda _e: self._render(True))
        self.bind("<Leave>", lambda _e: self._render(False))

    @property
    def full_text(self) -> str:
        return self._full

    def set_path(self, path: str) -> None:
        self._full = path
        self._render(False)

    def _render(self, full: bool) -> None:
        text = self._full if full else ellipsize_middle(self._full, self._max_chars)
        self.delete(0, "end")
        self.insert(0, text)

    def _on_key(self, event: tkinter.Event) -> str | None:
        ctrl = bool(event.state & 0x4)
        # Trả None cho phím hợp lệ: "break" sẽ chặn cả Tab (chuyển focus) và Ctrl+O (chọn ảnh).
        return "break" if is_edit_key(event.keysym, event.char, ctrl) else None


_KIND_STYLE: dict[NoticeKind, tuple[str, str, str]] = {
    # kind: (màu chữ/dải, màu nền, biểu tượng). Biểu tượng đi kèm chữ nên không dựa vào màu một mình.
    NoticeKind.ERROR: ("danger", "danger-bg", "✕"),
    NoticeKind.INFO: ("secondary", "secondary-bg", "ℹ"),
    NoticeKind.SUCCESS: ("success", "success-bg", "✓"),
}


class NoticeCard(ctk.CTkFrame):
    """Thẻ thông báo tại chỗ (spec 3.4): dải màu 4 px bên trái, biểu tượng, tiêu đề, nội dung, nút hành động."""

    def __init__(self, master: ctk.CTkBaseClass, notice: Notice, on_action: Callable[[Action], None]) -> None:
        accent, background, icon = _KIND_STYLE[notice.kind]
        super().__init__(master, fg_color=color(background), corner_radius=RADIUS_LG)
        self.notice = notice
        self.columnconfigure(1, weight=1)
        # height=1: dải không có con nên mặc định cao 200 và sẽ ép cả thẻ cao theo.
        stripe = ctk.CTkFrame(self, width=4, height=1, corner_radius=0, fg_color=color(accent))
        stripe.grid(row=0, column=0, sticky="ns", padx=(0, SPACE[4]))
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=0, column=1, sticky="ew", pady=SPACE[3], padx=(0, SPACE[4]))
        ctk.CTkLabel(
            body, text=f"{icon}  {notice.title}", font=font("heading"), text_color=color(accent), anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            body, text=notice.body, font=font("body"), text_color=color("text"), anchor="w", justify="left", wraplength=560
        ).pack(anchor="w", pady=(SPACE[1], 0))
        self.buttons: dict[Action, AppButton] = {}
        if notice.actions:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(anchor="w", pady=(SPACE[3], 0))
            for action in notice.actions:
                button = AppButton(row, ACTION_LABELS[action], lambda a=action: on_action(a), width=120)
                button.pack(side="left", padx=(0, SPACE[2]))
                self.buttons[action] = button


class ProgressRow(ctk.CTkFrame):
    """Thanh tiến độ cao 10 px kèm số phần trăm bằng chữ (spec 3.6). Chưa có % đầu tiên thì chạy chế độ không xác định."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self._bar = ctk.CTkProgressBar(
            self, height=10, corner_radius=5, fg_color=color("surface-alt"), progress_color=color("primary")
        )
        self._bar.grid(row=0, column=0, sticky="ew", padx=(0, SPACE[3]))
        self._percent = ctk.CTkLabel(self, text="", font=font("body-strong"), text_color=color("text"), width=48, anchor="e")
        self._percent.grid(row=0, column=1)
        self._status = ctk.CTkLabel(self, text="", font=font("caption"), text_color=color("text-muted"), anchor="w")
        self._status.grid(row=1, column=0, columnspan=2, sticky="w", pady=(SPACE[1], 0))
        self.indeterminate = False
        self.value_percent: float | None = None

    def show_starting(self) -> None:
        self.value_percent = None
        if not self.indeterminate:
            self.indeterminate = True
            self._bar.configure(mode="indeterminate")
            self._bar.start()
        self._percent.configure(text="")
        self._status.configure(text="Đang khởi động engine...")

    def set_percent(self, percent: float) -> None:
        if self.indeterminate:
            self.indeterminate = False
            self._bar.stop()
            self._bar.configure(mode="determinate")
        self.value_percent = percent
        self._bar.set(percent / 100)
        self._percent.configure(text=f"{round(percent)}%")
        self._status.configure(text="Đang xử lý ảnh...")

    def reset(self) -> None:
        if self.indeterminate:
            self._bar.stop()
        self.indeterminate = False
        self.value_percent = None
        self._bar.configure(mode="determinate")
        self._bar.set(0)
        self._percent.configure(text="")
        self._status.configure(text="")


class ConfirmCancelDialog(ctk.CTkToplevel):
    """Hộp thoại xác nhận hủy (spec 3.5). Focus đầu tiên ở nút an toàn, Esc đóng, grab_set khóa cửa sổ chính."""

    WIDTH = 420

    def __init__(self, master: ctk.CTkBaseClass, on_confirm: Callable[[], None], on_closed: Callable[[], None]) -> None:
        super().__init__(master, fg_color=color("surface"))
        self._on_confirm = on_confirm
        self._on_closed = on_closed
        self._closed = False
        self.title("Hủy xử lý")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.close)
        ctk.CTkLabel(self, text="Hủy xử lý ảnh này?", font=font("heading"), text_color=color("text"), anchor="w").pack(
            anchor="w", padx=SPACE[5], pady=(SPACE[5], SPACE[2])
        )
        ctk.CTkLabel(
            self,
            text="Hủy xử lý ảnh này? Ảnh gốc không bị ảnh hưởng và sẽ không có file kết quả.",
            font=font("body"),
            text_color=color("text"),
            anchor="w",
            justify="left",
            wraplength=self.WIDTH - 2 * SPACE[5],
        ).pack(anchor="w", padx=SPACE[5])
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=SPACE[5], pady=SPACE[5])
        # Secondary bên trái, Danger bên phải (spec 3.5).
        self.keep_button = AppButton(row, "Tiếp tục xử lý", self.close, "secondary", width=150)
        self.keep_button.pack(side="left")
        self.confirm_button = AppButton(row, "Hủy xử lý", self._confirm, "danger", width=120)
        self.confirm_button.pack(side="right")
        self.bind("<Escape>", lambda _e: self.close())
        self.update_idletasks()
        height = self.winfo_reqheight()
        parent = master.winfo_toplevel()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.WIDTH) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{self.WIDTH}x{height}+{max(x, 0)}+{max(y, 0)}")
        # CTkToplevel trên Windows hiện cửa sổ trễ; grab_set trước khi cửa sổ hiển thị sẽ lỗi.
        self.after(100, self._grab_and_focus)

    def _grab_and_focus(self) -> None:
        if self._closed:
            return
        try:
            self.grab_set()
        except tkinter.TclError:
            pass  # không khóa được thì hộp thoại vẫn dùng được, chỉ mất tính modal
        self.keep_button._canvas.focus_set()

    def _confirm(self) -> None:
        self.close()
        self._on_confirm()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except tkinter.TclError:
            pass
        self.destroy()
        self._on_closed()
