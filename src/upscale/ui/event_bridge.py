"""Đưa sự kiện từ luồng worker về luồng chính.

Tkinter chỉ an toàn khi cập nhật widget từ luồng chính. Luồng worker gọi `push` (an toàn
giữa các luồng, vì queue.Queue có khóa nội bộ). Luồng chính hỏi hàng đợi định kỳ bằng
`after` và gọi `handler`. Đây là chỗ duy nhất giữ ràng buộc luồng của Tkinter.
"""
from __future__ import annotations

import logging
import queue
import tkinter
from collections.abc import Callable
from typing import Generic, Protocol, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")


class Scheduler(Protocol):
    """Phần của widget Tk mà EventBridge cần. Tách ra để test không cần cửa sổ thật."""

    def after(self, ms: int, func: Callable[[], object]) -> str: ...

    def after_cancel(self, id: str) -> None: ...


class EventBridge(Generic[T]):
    def __init__(
        self,
        scheduler: Scheduler,
        handler: Callable[[T], None],
        interval_ms: int = 50,
        max_per_tick: int = 100,
    ) -> None:
        self._scheduler = scheduler
        self._handler = handler
        self._interval_ms = interval_ms
        self._max_per_tick = max_per_tick
        self._queue: queue.Queue[T] = queue.Queue()
        self._after_id: str | None = None
        self._closed = False

    def push(self, item: T) -> None:
        """Gọi được từ bất kỳ luồng nào. Sau khi đóng thì bỏ qua."""
        if not self._closed:
            self._queue.put(item)

    def start(self) -> None:
        if self._after_id is None and not self._closed:
            self._after_id = self._scheduler.after(self._interval_ms, self._tick)

    def close(self) -> None:
        """Dừng hỏi hàng đợi và bỏ các sự kiện chưa xử lý. Gọi khi đóng cửa sổ."""
        self._closed = True
        if self._after_id is not None:
            try:
                self._scheduler.after_cancel(self._after_id)
            except tkinter.TclError:
                log.debug("after_cancel thất bại, cửa sổ có thể đã bị hủy")
            self._after_id = None
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _tick(self) -> None:
        self._after_id = None
        # Giới hạn số sự kiện mỗi lượt để một đợt dồn sự kiện không làm giao diện đứng.
        for _ in range(self._max_per_tick):
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._handler(item)
            except Exception:  # lỗi ở một handler không được làm chết vòng lặp
                log.exception("Handler sự kiện giao diện ném ngoại lệ")
        if not self._closed:
            self._after_id = self._scheduler.after(self._interval_ms, self._tick)
