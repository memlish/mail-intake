"""An in-memory store of message summaries. A restart clears it."""

from __future__ import annotations

import itertools
import threading
from collections import OrderedDict

from .parsing import Summary


class Inbox:
    """Keeps the newest summaries, up to a fixed number."""

    def __init__(self, keep: int) -> None:
        self._keep = max(1, keep)
        self._items: OrderedDict[int, Summary] = OrderedDict()
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def add(self, summary: Summary) -> int:
        with self._lock:
            message_id = next(self._ids)
            self._items[message_id] = summary
            while len(self._items) > self._keep:
                self._items.popitem(last=False)
            return message_id

    def get(self, message_id: int) -> Summary | None:
        with self._lock:
            return self._items.get(message_id)

    def newest_first(self, sender: str | None = None) -> list[tuple[int, Summary]]:
        with self._lock:
            items = list(self._items.items())
        if sender:
            items = [item for item in items if item[1].sender.lower() == sender.lower()]
        return list(reversed(items))

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
