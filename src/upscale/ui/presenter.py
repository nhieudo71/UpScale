"""Chuyển dữ liệu domain thành nội dung hiển thị tiếng Việt. Thuần Python, không import Tk.

Tách khỏi views.py để kiểm thử nội dung (thông báo lỗi, định dạng) mà không cần cửa sổ.
Nội dung theo docs/UX-UI-SPEC.md mục 4.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..domain.models import SUPPORTED_SCALES, ErrorCode, ImageInfo
from ..domain.rules import output_size


class NoticeKind(str, Enum):
    ERROR = "error"
    INFO = "info"
    SUCCESS = "success"


class Action(str, Enum):
    PICK = "pick"
    OPEN_PROJECT = "open_project"
    SET_2X = "set_2x"
    RETRY = "retry"
    OPEN_LOG = "open_log"
    QUIT = "quit"


ACTION_LABELS: dict[Action, str] = {
    Action.PICK: "Chọn ảnh khác",
    Action.OPEN_PROJECT: "Mở thư mục dự án",
    Action.SET_2X: "Chọn 2x",
    Action.RETRY: "Thử lại",
    Action.OPEN_LOG: "Mở file log",
    Action.QUIT: "Thoát",
}

SCALE_LABELS: dict[int, str] = {2: "2x (gấp đôi)", 4: "4x (gấp bốn)"}
SCALE_OPTIONS: tuple[tuple[str, str], ...] = tuple((str(s), SCALE_LABELS[s]) for s in SUPPORTED_SCALES)


@dataclass(frozen=True)
class Notice:
    kind: NoticeKind
    title: str
    body: str
    actions: tuple[Action, ...] = ()


def notice_for_error(code: ErrorCode, message: str | None, scale: int) -> Notice:
    """Thẻ thông báo cho một mã lỗi. Ưu tiên `message` của service vì nó có chi tiết (đường dẫn, kích thước)."""
    text = (message or "").strip()
    if code is ErrorCode.CANCELLED:
        return Notice(NoticeKind.INFO, "Đã hủy", "Không tạo file kết quả. Ảnh gốc không bị ảnh hưởng.")
    if code is ErrorCode.IMAGE_UNREADABLE:
        return Notice(NoticeKind.ERROR, "Không đọc được ảnh",
                      text or "File này không phải ảnh PNG/JPG hợp lệ hoặc đã bị hỏng.", (Action.PICK,))
    if code is ErrorCode.ENGINE_MISSING:
        return Notice(NoticeKind.ERROR, "Thiếu engine hoặc model",
                      text or "Không tìm thấy engine. Hãy chép lại thư mục engine\\realesrgan.", (Action.OPEN_PROJECT,))
    if code is ErrorCode.OUTPUT_TOO_LARGE:
        # Đã ở 2x thì không còn hệ số nhỏ hơn để gợi ý.
        return Notice(NoticeKind.ERROR, "Ảnh kết quả quá lớn",
                      text or "Ảnh kết quả vượt giới hạn máy này xử lý an toàn.",
                      (Action.SET_2X,) if scale > 2 else ())
    if code is ErrorCode.OUT_OF_VRAM:
        return Notice(NoticeKind.ERROR, "Không đủ bộ nhớ GPU",
                      text or "Card đồ họa hết bộ nhớ khi xử lý ảnh này. Hãy thử hệ số 2x.",
                      (Action.RETRY, Action.OPEN_LOG))
    if code is ErrorCode.BUSY:
        return Notice(NoticeKind.INFO, "Đang bận", text or "Đang xử lý một ảnh khác. Hãy chờ xong hoặc hủy.")
    return Notice(NoticeKind.ERROR, "Xử lý không thành công",
                  text or "Engine dừng với lỗi. Ảnh gốc không bị ảnh hưởng.", (Action.RETRY, Action.OPEN_LOG))


def describe_scale(info: ImageInfo, scale: int) -> str:
    out_w, out_h = output_size(info.width, info.height, scale)
    return f"{info.width} x {info.height} thành {out_w} x {out_h}"


def ellipsize_middle(text: str, max_chars: int) -> str:
    """Cắt giữa chuỗi dài bằng '...' (spec 3.3), giữ đầu và đuôi đường dẫn. Kết quả dài đúng max_chars."""
    if max_chars < 5 or len(text) <= max_chars:
        return text
    keep = max_chars - 3
    head = (keep + 1) // 2
    tail = keep // 2
    return text[:head] + "..." + text[len(text) - tail :]


def format_duration(duration_ms: int) -> str:
    seconds = max(duration_ms, 0) / 1000
    if seconds < 60:
        return f"{seconds:.1f}".replace(".", ",") + " giây"
    minutes, rest = divmod(int(seconds), 60)
    return f"{minutes} phút {rest} giây"


def was_renamed(source: str, output: str, scale: int) -> bool:
    """True nếu tên file kết quả có hậu tố số vì trùng tên."""
    return Path(output).name != f"{Path(source).stem}_x{scale}.png"


def done_notice(source: str, output: str, scale: int, out_w: int, out_h: int, duration_ms: int) -> Notice:
    body = f"Thời gian xử lý: {format_duration(duration_ms)}."
    if was_renamed(source, output, scale):
        body += f" Đã có file cùng tên, ảnh được lưu thành {Path(output).name}."
    return Notice(NoticeKind.SUCCESS, f"Đã lưu ảnh {out_w} x {out_h}", body)
