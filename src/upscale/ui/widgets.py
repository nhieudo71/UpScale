"""Nút và nhóm nút chọn một. CustomTkinter 6.0.0 mặc định không cho Tab vào nút và không có Enter/Space,
nên hai lớp này tự bật takefocus, gắn phím và vẽ vòng focus (spec mục 1 "Bàn phím", mục 3.1, 3.2)."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from .theme import CONTROL_HEIGHT, RADIUS_MD, RADIUS_SM, color, font

_VARIANTS: dict[str, dict[str, str | None]] = {
    "primary": {"fg": "primary", "hover": "primary-hover", "text": "on-primary", "border": None, "ring": "text"},
    "secondary": {"fg": "surface-alt", "hover": "secondary-hover", "text": "text", "border": "border", "ring": "primary"},
    "danger": {"fg": "danger", "hover": "danger-hover", "text": "on-danger", "border": None, "ring": "text"},
}


class AppButton(ctk.CTkButton):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        text: str,
        command: Callable[[], None],
        variant: str = "secondary",
        width: int = 140,
    ) -> None:
        spec = _VARIANTS[variant]
        self._spec = spec
        self._base_border = 1 if spec["border"] else 0
        self._enabled = True
        super().__init__(
            master,
            text=text,
            width=width,
            height=CONTROL_HEIGHT,
            corner_radius=RADIUS_MD,
            border_width=self._base_border,
            border_color=color(spec["border"] or "border"),
            fg_color=color(spec["fg"]),
            hover_color=color(spec["hover"]),
            text_color=color(spec["text"]),
            text_color_disabled=color("text-muted"),
            font=font("body-strong"),
            command=command,
        )
        self._canvas.configure(takefocus=1)
        self._canvas.bind("<FocusIn>", self._focus_in, add="+")
        self._canvas.bind("<FocusOut>", self._focus_out, add="+")
        for sequence in ("<Return>", "<space>"):
            self._canvas.bind(sequence, self._on_key, add="+")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool, text: str | None = None) -> None:
        self._enabled = enabled
        if text is not None:
            self.configure(text=text)
        if enabled:
            self.configure(
                state="normal",
                fg_color=color(self._spec["fg"]),
                border_width=self._base_border,
                border_color=color(self._spec["border"] or "border"),
            )
        else:
            # Spec 3.1: disabled = nền surface-alt, chữ text-muted. Thêm viền để nút khóa vẫn thấy được hình.
            self.configure(state="disabled", fg_color=color("surface-alt"), border_width=1, border_color=color("border"))
        self._canvas.configure(takefocus=1 if enabled else 0)

    def _on_key(self, _event: object) -> str:
        if self._enabled:
            self.invoke()
        return "break"

    def _focus_in(self, _event: object) -> None:
        if self._enabled:
            self.configure(border_width=2, border_color=color(self._spec["ring"]))

    def _focus_out(self, _event: object) -> None:
        if self._enabled:
            self.configure(border_width=self._base_border, border_color=color(self._spec["border"] or "border"))


class Segmented(ctk.CTkFrame):
    """Chọn đúng một mục. Mục đang chọn có dấu tích (không chỉ dựa vào màu). Mũi tên trái/phải đổi mục."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        options: list[tuple[str, str]],
        value: str,
        command: Callable[[str], None],
        min_width: int = 72,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._values = [v for v, _ in options]
        if value not in self._values:
            raise ValueError(f"value {value!r} không nằm trong {self._values}")
        self._labels = dict(options)
        self._value = value
        self._command = command
        self._enabled = True
        self._buttons: dict[str, ctk.CTkButton] = {}
        measure = font("body-strong")
        for index, (key, label) in enumerate(options):
            width = max(min_width, measure.measure("✓ " + label) + 32)
            button = ctk.CTkButton(
                self,
                text=label,
                width=width,
                height=CONTROL_HEIGHT,
                corner_radius=RADIUS_SM,
                border_width=1,
                border_color=color("border"),
                font=font("body-strong"),
                command=lambda k=key: self._select(k, focus=True),
            )
            button.grid(row=0, column=index, padx=(0, 8) if index < len(options) - 1 else 0)
            button._canvas.configure(takefocus=1)
            button._canvas.bind("<FocusIn>", lambda _e, b=button: self._ring(b, True), add="+")
            button._canvas.bind("<FocusOut>", lambda _e, b=button: self._ring(b, False), add="+")
            button._canvas.bind("<Return>", lambda _e, k=key: self._key_select(k), add="+")
            button._canvas.bind("<space>", lambda _e, k=key: self._key_select(k), add="+")
            button._canvas.bind("<Left>", lambda _e, k=key: self._step(k, -1), add="+")
            button._canvas.bind("<Right>", lambda _e, k=key: self._step(k, 1), add="+")
            self._buttons[key] = button
        self._apply()

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, value: str) -> None:
        if value in self._buttons and value != self._value:
            self._value = value
            self._apply()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        for button in self._buttons.values():
            button.configure(state="normal" if enabled else "disabled")
            button._canvas.configure(takefocus=1 if enabled else 0)
        self._apply()

    def _select(self, key: str, focus: bool = False) -> None:
        if not self._enabled:
            return
        changed = key != self._value
        self._value = key
        self._apply()
        if focus:
            self._buttons[key]._canvas.focus_set()
        if changed:
            self._command(key)

    def _key_select(self, key: str) -> str:
        self._select(key)
        return "break"

    def _step(self, key: str, delta: int) -> str:
        target = self._values[(self._values.index(key) + delta) % len(self._values)]
        self._select(target, focus=True)
        return "break"

    def _ring(self, button: ctk.CTkButton, focused: bool) -> None:
        if self._enabled:
            button.configure(border_width=2 if focused else 1, border_color=color("text" if focused else "border"))

    def _apply(self) -> None:
        for key, button in self._buttons.items():
            selected = key == self._value
            button.configure(
                text=("✓ " if selected else "") + self._labels[key],
                fg_color=color("primary" if selected else "surface-alt"),
                hover_color=color("primary-hover" if selected else "secondary-hover"),
                text_color=color("on-primary" if selected else "text"),
                text_color_disabled=color("on-primary" if selected else "text-muted"),
            )
