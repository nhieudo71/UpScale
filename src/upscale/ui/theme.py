"""Design token theo docs/UX-UI-SPEC.md mục 2. Component chỉ dùng tên token, không ghi mã màu trực tiếp."""
from __future__ import annotations

import tkinter.font as tkfont

import customtkinter as ctk

# (sáng, tối). CustomTkinter nhận tuple này và tự đổi theo appearance mode.
TOKENS: dict[str, tuple[str, str]] = {
    "bg": ("#F6F7F9", "#0E1015"),
    "surface": ("#FFFFFF", "#161920"),
    "surface-alt": ("#EEF0F4", "#1F232C"),
    "border": ("#7A8394", "#6B7385"),
    "text": ("#171A21", "#ECEEF2"),
    "text-muted": ("#4A5160", "#A7AEBC"),
    "primary": ("#4338CA", "#6E72F5"),
    "primary-hover": ("#3730A3", "#8084F8"),
    "on-primary": ("#FFFFFF", "#0E1015"),
    "secondary": ("#0B6370", "#4FD1D9"),
    "secondary-bg": ("#E2F3F5", "#12303A"),
    "danger": ("#B42318", "#FF8A80"),
    "danger-bg": ("#FDECEA", "#3A1A19"),
    "on-danger": ("#FFFFFF", "#0E1015"),
    "success": ("#146C43", "#5FD398"),
    "success-bg": ("#E6F4EC", "#16301F"),
    "warning": ("#8A4B00", "#F5B454"),
    "warning-bg": ("#FFF4E0", "#33260F"),
    # Hai token dưới KHÔNG có trong spec (spec mục 2.1 ghi "chưa tính màu hover nút phụ và nút nguy hiểm").
    # Giá trị do tôi chọn, độ tương phản được kiểm trong tests/test_ui_theme.py.
    "secondary-hover": ("#E0E3EA", "#2B303B"),
    "danger-hover": ("#912018", "#FFA8A0"),
}

SPACE = {1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32}
RADIUS_SM, RADIUS_MD, RADIUS_LG = 6, 10, 14
CONTROL_HEIGHT = 40
WINDOW_MIN = (760, 560)
WINDOW_DEFAULT = (960, 640)

# token -> (dùng font mono, cỡ pt, đậm)
_FONT_SPECS: dict[str, tuple[bool, int, bool]] = {
    "title": (False, 20, True),
    "heading": (False, 14, True),
    "body": (False, 11, False),
    "body-strong": (False, 11, True),
    "caption": (False, 10, False),
    "mono": (True, 10, False),
}
_SANS = ("Segoe UI Variable Text", "Segoe UI")
_MONO = ("Consolas", "Courier New")


def color(name: str) -> tuple[str, str]:
    return TOKENS[name]


def pick_family(available: set[str], preferred: tuple[str, ...]) -> str:
    """Chọn font đầu tiên có trên máy; không có thì để Tk chọn font mặc định."""
    for family in preferred:
        if family in available:
            return family
    return "TkDefaultFont"


def points_to_ctk_size(points: int) -> int:
    """CTkFont.size tính bằng pixel (CustomTkinter dùng cỡ âm của Tk), không phải pt.

    Spec ghi cỡ bằng pt, nên đổi theo 96 DPI: px = pt * 4/3. CustomTkinter nhân thêm hệ số
    co giãn của màn hình sau đó.
    """
    return round(points * 4 / 3)


def font(token: str) -> ctk.CTkFont:
    """Tạo mới mỗi lần gọi (không cache) vì CTkFont gắn với một root Tk; test tạo nhiều root."""
    mono, points, bold = _FONT_SPECS[token]
    family = pick_family(set(tkfont.families()), _MONO if mono else _SANS)
    return ctk.CTkFont(family=family, size=points_to_ctk_size(points), weight="bold" if bold else "normal")


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Tỉ lệ tương phản WCAG 2.x giữa hai màu '#RRGGBB'."""

    def channel(value: int) -> float:
        s = value / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    def luminance(hex_color: str) -> float:
        r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

    lighter, darker = sorted((luminance(fg_hex), luminance(bg_hex)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)
