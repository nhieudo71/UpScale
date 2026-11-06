"""Cửa sổ chính UpScale: một màn hình, bốn trạng thái S0 đến S3 và màn hình M1 (thiếu engine).

Chỉ gọi UpscaleService. Sự kiện job đến từ luồng worker và được EventBridge chuyển về luồng Tk.
"""
from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from tkinter import TclError, filedialog

import customtkinter as ctk

from ..domain.models import DEFAULT_MODEL, MODELS, ErrorCode, EventType, ImageInfo, JobEvent, UpscaleError, UpscaleRequest
from ..domain.rules import check_output_limit
from ..infra.config import Config, load_config
from ..infra.logging_setup import setup_logging
from ..services.upscale_service import UpscaleService
from .event_bridge import EventBridge
from .presenter import SCALE_OPTIONS, Action, Notice, NoticeKind, describe_scale, done_notice, notice_for_error
from .theme import RADIUS_LG, SPACE, WINDOW_DEFAULT, WINDOW_MIN, color, font
from .views import ConfirmCancelDialog, NoticeCard, PathField, ProgressRow
from .widgets import AppButton, Segmented

log = logging.getLogger(__name__)


class State(str, Enum):
    S0 = "S0"  # chưa chọn ảnh
    S1 = "S1"  # đã chọn ảnh
    S2 = "S2"  # đang xử lý
    S3 = "S3"  # hoàn tất
    M1 = "M1"  # thiếu engine hoặc model


# Phần nào của thẻ chính hiện ở trạng thái nào. Thứ tự hàng trong thẻ theo thứ tự trong App._build.
VISIBLE: dict[State, frozenset[str]] = {
    State.S0: frozenset({"hint", "pick"}),
    State.S1: frozenset({"pick", "info", "options", "actions"}),
    State.S2: frozenset({"pick", "info", "options", "actions", "progress"}),
    State.S3: frozenset({"info", "result"}),
    State.M1: frozenset(),
}


def find_missing_engine_files(config: Config) -> list[Path]:
    """Engine và model mặc định. Model anime thiếu thì chỉ báo lỗi khi người dùng chọn nó."""
    name = MODELS[DEFAULT_MODEL].engine_name
    required = [config.engine_exe, config.models_dir / f"{name}.param", config.models_dir / f"{name}.bin"]
    return [path for path in required if not path.exists()]


def ask_image_path() -> str:
    return filedialog.askopenfilename(
        title="Chọn ảnh", filetypes=[("Ảnh PNG hoặc JPG", "*.png *.jpg *.jpeg"), ("Tất cả file", "*.*")]
    )


def open_in_shell(path: Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]  # chỉ có trên Windows
    except (OSError, AttributeError):
        log.warning("Không mở được %s", path, exc_info=True)


def _caption(master: ctk.CTkBaseClass, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=text, font=font("caption"), text_color=color("text-muted"), anchor="w")


class App(ctk.CTk):
    def __init__(
        self,
        config: Config,
        service: UpscaleService | None = None,
        ask_open_file: Callable[[], str] = ask_image_path,
        open_path: Callable[[Path], None] = open_in_shell,
    ) -> None:
        super().__init__(fg_color=color("bg"))
        self._config = config
        self._service = service or UpscaleService(config)
        self._ask_open_file = ask_open_file
        self._open_path = open_path
        self._state = State.S0
        self._image: ImageInfo | None = None
        self._job_id: str | None = None
        self._output_path: str | None = None
        self._dialog: ConfirmCancelDialog | None = None
        self._notice_card: NoticeCard | None = None
        self._sections: dict[str, ctk.CTkBaseClass] = {}
        self.title("UpScale")
        self.minsize(*WINDOW_MIN)
        self.geometry(f"{WINDOW_DEFAULT[0]}x{WINDOW_DEFAULT[1]}")
        self._bridge: EventBridge[JobEvent] = EventBridge(self, self._on_job_event)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-o>", lambda _e: self._pick())
        self.bind("<Escape>", lambda _e: self._ask_cancel())
        self._bridge.start()
        missing = find_missing_engine_files(config)
        if missing:
            self._enter_missing(missing)
        else:
            self._set_state(State.S0)


    def _build(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        # Đệm dọc 16 px (không phải 32) để S1 và S2 vừa cửa sổ tối thiểu 760x560 của spec.
        body.pack(fill="both", expand=True, padx=SPACE[6], pady=SPACE[4])
        body.columnconfigure(0, weight=1)
        header = ctk.CTkFrame(body, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, SPACE[3]))
        ctk.CTkLabel(header, text="UpScale", font=font("title"), text_color=color("text"), anchor="w").pack(side="left")
        # Cùng hàng với tiêu đề để tiết kiệm một dòng chiều cao; cửa sổ tối thiểu 560 px rất chật.
        _caption(header, "Phóng to ảnh bằng AI, chạy ngay trên máy của bạn.").pack(
            side="left", anchor="s", padx=(SPACE[3], 0), pady=(0, SPACE[1]))
        # CTkFrame rỗng giữ chiều cao mặc định 200, nên phải đặt 1 để khung chỉ cao khi có thẻ thông báo.
        self._notice_slot = ctk.CTkFrame(body, fg_color="transparent", width=1, height=1)
        self._notice_slot.grid(row=1, column=0, sticky="ew")
        self._notice_slot.columnconfigure(0, weight=1)
        card = ctk.CTkFrame(body, fg_color=color("surface"), border_width=1,
                            border_color=color("border"), corner_radius=RADIUS_LG)
        card.grid(row=2, column=0, sticky="ew", pady=(SPACE[3], 0))
        card.columnconfigure(0, weight=1)
        self._card = card
        # Thứ tự tạo widget quyết định thứ tự Tab: Chọn ảnh, 2x, 4x, model, Upscale, Hủy, Mở thư mục.
        self._sections["hint"] = ctk.CTkLabel(
            card, text="Chọn một ảnh PNG hoặc JPG để phóng to. Ảnh gốc không bị thay đổi.",
            font=font("body"), text_color=color("text"), anchor="w")
        self._pick_button = AppButton(card, "Chọn ảnh", self._pick, "secondary", width=160)
        self._sections["pick"] = self._pick_button

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.columnconfigure(0, weight=1)
        self._name_label = ctk.CTkLabel(info, text="", font=font("body-strong"), text_color=color("text"), anchor="w")
        self._name_label.grid(row=0, column=0, sticky="w")
        _caption(info, "Đường dẫn ảnh").grid(row=1, column=0, columnspan=2, sticky="w", pady=(SPACE[2], 0))
        self._image_path = PathField(info)
        self._image_path.grid(row=2, column=0, columnspan=2, sticky="ew")
        self._dims_label = ctk.CTkLabel(info, text="", font=font("body"), text_color=color("text"), anchor="e")
        self._dims_label.grid(row=0, column=1, sticky="e", padx=(SPACE[4], 0))
        self._sections["info"] = info

        options = ctk.CTkFrame(card, fg_color="transparent")
        _caption(options, "Hệ số phóng to").grid(row=0, column=0, sticky="w")
        _caption(options, "Loại ảnh").grid(row=0, column=1, sticky="w", padx=(SPACE[6], 0))
        self._scale_seg = Segmented(options, list(SCALE_OPTIONS), "4", self._on_scale_changed)
        self._scale_seg.grid(row=1, column=0, sticky="w", pady=(SPACE[1], 0))
        self._model_seg = Segmented(options, [(m.key, m.label) for m in self._service.list_models()],
                                    DEFAULT_MODEL, lambda _key: None)
        self._model_seg.grid(row=1, column=1, sticky="w", padx=(SPACE[6], 0), pady=(SPACE[1], 0))
        self._sections["options"] = options

        actions = ctk.CTkFrame(card, fg_color="transparent")
        self._upscale_button = AppButton(actions, "Upscale", self._start, "primary", width=160)
        self._upscale_button.pack(side="left")
        self._cancel_button = AppButton(actions, "Hủy", self._ask_cancel, "danger", width=120)
        self._sections["actions"] = actions

        self._progress = ProgressRow(card)
        self._sections["progress"] = self._progress

        result = ctk.CTkFrame(card, fg_color="transparent")
        result.columnconfigure(0, weight=1)
        _caption(result, "Ảnh kết quả").grid(row=0, column=0, sticky="w")
        self._result_path = PathField(result)
        self._result_path.grid(row=1, column=0, sticky="ew")
        buttons = ctk.CTkFrame(result, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="w", pady=(SPACE[3], 0))
        self._open_button = AppButton(buttons, "Mở thư mục", self._open_folder, "primary", width=160)
        self._open_button.pack(side="left")
        self._another_button = AppButton(buttons, "Upscale ảnh khác", self._reset_to_s0, "secondary", width=180)
        self._another_button.pack(side="left", padx=(SPACE[3], 0))
        self._sections["result"] = result

    def _layout(self, visible: frozenset[str]) -> None:
        """Hiện đúng các phần của trạng thái hiện tại, giữ nguyên thứ tự hàng."""
        row = 0
        for index in range(len(self._sections) + 1):
            self._card.grid_rowconfigure(index, minsize=0)  # xóa hàng đệm của trạng thái trước
        for name, widget in self._sections.items():
            if name in visible:
                widget.grid(row=row, column=0, sticky="w" if name in ("hint", "pick") else "ew",
                            padx=SPACE[5], pady=(SPACE[5] if row == 0 else SPACE[3], 0))
                row += 1
            else:
                widget.grid_remove()
        self._card.grid_rowconfigure(row, minsize=SPACE[4])


    # ---- Trạng thái ----
    def _scale(self) -> int:
        return int(self._scale_seg.value)

    def _set_state(self, state: State) -> None:
        self._state = state
        visible = VISIBLE[state]
        if visible:
            self._card.grid()
        else:
            self._card.grid_remove()
        self._layout(visible)
        busy = state is State.S2
        self._pick_button.set_enabled(not busy)
        self._scale_seg.set_enabled(not busy)
        self._model_seg.set_enabled(not busy)
        self._upscale_button.set_enabled(not busy, "Đang xử lý..." if busy else "Upscale")
        if busy:
            self._cancel_button.set_enabled(True, "Hủy")
            self._cancel_button.pack(side="left", padx=(SPACE[3], 0))
        else:
            self._cancel_button.pack_forget()
            self._progress.reset()
        if self._image is not None and state in (State.S1, State.S2, State.S3):
            self._name_label.configure(text=Path(self._image.path).name)
            self._image_path.set_path(self._image.path)
            self._update_dims()
        self._focus_for(state)

    def _focus_for(self, state: State) -> None:
        target = {
            State.S0: self._pick_button,
            State.S1: self._upscale_button,
            State.S2: self._cancel_button,
            State.S3: self._open_button,
        }.get(state)
        if target is not None:
            try:
                target._canvas.focus_set()
            except TclError:
                log.debug("Không đặt được focus cho %s", state)

    def _update_dims(self) -> None:
        if self._image is not None:
            self._dims_label.configure(text=describe_scale(self._image, self._scale()))

    def _show_notice(self, notice: Notice | None) -> None:
        old = self._notice_card
        self._notice_card = None
        if old is not None:
            old.grid_forget()
            # Hàm này có thể đang chạy bên trong lệnh của chính một nút trên thẻ cũ.
            # Hủy ngay widget đó sẽ để lại callback hoạt ảnh nút trỏ vào widget đã mất, nên hoãn việc hủy.
            self.after(300, old.destroy)
        if notice is not None:
            card = NoticeCard(self._notice_slot, notice, self._handle_action)
            card.grid(row=0, column=0, sticky="ew")
            self._notice_card = card

    def _enter_missing(self, missing: list[Path]) -> None:
        lines = "\n".join(str(path) for path in missing)
        self._show_notice(Notice(
            NoticeKind.ERROR,
            "Thiếu engine hoặc model",
            f"Không tìm thấy:\n{lines}\nHãy chép lại thư mục engine\\realesrgan rồi mở lại ứng dụng.",
            (Action.OPEN_PROJECT, Action.QUIT),
        ))
        self._set_state(State.M1)
        if self._notice_card is not None and self._notice_card.buttons:
            first = next(iter(self._notice_card.buttons.values()))
            first._canvas.focus_set()

    def _fail(self, code: ErrorCode, message: str | None) -> None:
        self._job_id = None
        self._show_notice(notice_for_error(code, message, self._scale()))
        self._set_state(State.S1)

    # ---- Hành động của người dùng ----
    def _pick(self) -> None:
        if self._state not in (State.S0, State.S1, State.S3):
            return
        path = self._ask_open_file()
        if not path:
            return
        try:
            info = self._service.inspect_image(path)
        except UpscaleError as exc:
            self._image = None
            self._show_notice(notice_for_error(exc.code, exc.message, self._scale()))
            self._set_state(State.S0)  # E1: về S0, app dùng tiếp được
            return
        self._image = info
        self._show_notice(None)
        self._set_state(State.S1)

    def _on_scale_changed(self, _key: str) -> None:
        self._show_notice(None)
        self._update_dims()

    def _start(self) -> None:
        if self._state is not State.S1 or self._image is None:
            return
        scale = self._scale()
        try:
            # E2: chặn trước khi chạy, ở lại S1.
            check_output_limit(self._image.width, self._image.height, scale, self._config.max_output_pixels)
        except UpscaleError as exc:
            self._fail(exc.code, exc.message)
            return
        request = UpscaleRequest(self._image.path, scale=scale, model=self._model_seg.value)
        self._show_notice(None)
        self._set_state(State.S2)
        self._progress.show_starting()
        try:
            self._job_id = self._service.start(request, self._bridge.push)
        except UpscaleError as exc:
            self._fail(exc.code, exc.message)
    def _ask_cancel(self) -> None:
        """Esc và nút Hủy: mở hộp thoại xác nhận. Ngoài S2 hoặc khi hộp thoại đang mở thì không làm gì."""
        if self._state is not State.S2 or self._dialog is not None:
            return
        self._dialog = ConfirmCancelDialog(self, self._confirm_cancel, self._dialog_closed)

    def _confirm_cancel(self) -> None:
        # Job có thể đã xong trong lúc hộp thoại mở; khi đó sự kiện done/failed đã đưa app ra khỏi S2.
        if self._state is State.S2 and self._job_id is not None:
            self._service.cancel(self._job_id)
            self._progress.show_starting()
            self._cancel_button.set_enabled(False, "Đang hủy...")

    def _dialog_closed(self) -> None:
        self._dialog = None
        if self._state is State.S2 and self._cancel_button.enabled:
            self._focus_for(State.S2)  # trả focus về nút đã mở hộp thoại

    def _close_dialog(self) -> None:
        if self._dialog is not None:
            self._dialog.close()

    # ---- Sự kiện job (đã ở luồng Tk nhờ EventBridge) ----
    def _on_job_event(self, event: JobEvent) -> None:
        if event.job_id != self._job_id or self._state is not State.S2:
            return  # sự kiện muộn của job cũ
        if event.type is EventType.PROGRESS and event.percent is not None:
            self._progress.set_percent(event.percent)
        elif event.type is EventType.DONE:
            self._close_dialog()
            self._finish(event)
        elif event.type is EventType.FAILED:
            self._close_dialog()
            self._fail(event.code or ErrorCode.ENGINE_FAILED, event.message)

    def _finish(self, event: JobEvent) -> None:
        self._job_id = None
        if self._image is None or event.output_path is None:
            self._fail(ErrorCode.ENGINE_FAILED, "Không nhận được đường dẫn ảnh kết quả.")
            return
        self._output_path = event.output_path
        self._result_path.set_path(event.output_path)
        self._show_notice(done_notice(
            self._image.path, event.output_path, self._scale(),
            event.output_w or 0, event.output_h or 0, event.duration_ms or 0,
        ))
        self._set_state(State.S3)

    # ---- Hành động trên thẻ thông báo và màn hình kết quả ----
    def _handle_action(self, action: Action) -> None:
        if action is Action.PICK:
            self._pick()
        elif action is Action.OPEN_PROJECT:
            self._open_path(self._config.project_root)
        elif action is Action.SET_2X:
            self._scale_seg.set_value("2")
            self._on_scale_changed("2")
            self._focus_for(State.S1)
        elif action is Action.RETRY:
            self._start()
        elif action is Action.OPEN_LOG:
            self._open_path(self._config.log_dir / "app.log")
        elif action is Action.QUIT:
            self._on_close()

    def _open_folder(self) -> None:
        if self._output_path:
            self._open_path(Path(self._output_path).parent)

    def _reset_to_s0(self) -> None:
        self._image = None
        self._output_path = None
        self._show_notice(None)
        self._set_state(State.S0)

    def _on_close(self) -> None:
        self._close_dialog()
        self._bridge.close()
        try:
            self._service.shutdown()
        finally:
            self.destroy()


def main() -> int:
    config = load_config()
    setup_logging(config.log_dir)
    ctk.set_appearance_mode("system")
    try:
        App(config).mainloop()
    except Exception:
        log.exception("Ứng dụng thoát vì lỗi không lường trước")
        print("UpScale gặp lỗi không lường trước. Xem chi tiết trong logs\\app.log.", file=sys.stderr)
        return 1
    return 0
