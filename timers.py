import threading
import time
from typing import Callable, Optional


class TimerEntry:
    def __init__(self, total: float, on_end: Callable):
        self.start_time = time.time()
        self.total = total
        self.on_end = on_end
        self._thread: Optional[threading.Timer] = None

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def remaining(self) -> float:
        return max(0.0, self.total - self.elapsed)

    @property
    def progress(self) -> float:
        """0.0 à 1.0"""
        return min(1.0, self.elapsed / self.total)


class TimerManager:
    def __init__(self):
        self._timers: dict[tuple, TimerEntry] = {}
        self._lock = threading.Lock()

    def start(self, survivor_idx: int, name: str, duration: float, on_end: Callable):
        key = (survivor_idx, name)
        with self._lock:
            self._cancel_unsafe(key)
            entry = TimerEntry(duration, on_end)
            entry._thread = threading.Timer(duration, self._fire, args=[key])
            entry._thread.daemon = True
            entry._thread.start()
            self._timers[key] = entry

    def cancel(self, survivor_idx: int, name: str):
        key = (survivor_idx, name)
        with self._lock:
            self._cancel_unsafe(key)

    def _cancel_unsafe(self, key: tuple):
        if key in self._timers:
            self._timers[key]._thread.cancel()
            del self._timers[key]

    def add_time(self, survivor_idx: int, name: str, seconds: float):
        """Ajoute du temps à un timer existant (wiggle bonus)."""
        key = (survivor_idx, name)
        with self._lock:
            if key not in self._timers:
                return
            entry = self._timers[key]
            entry.total += seconds
            entry._thread.cancel()
            remaining = entry.remaining
            entry._thread = threading.Timer(remaining, self._fire, args=[key])
            entry._thread.daemon = True
            entry._thread.start()

    def is_active(self, survivor_idx: int, name: str) -> bool:
        return (survivor_idx, name) in self._timers

    def get_remaining(self, survivor_idx: int, name: str) -> Optional[float]:
        entry = self._timers.get((survivor_idx, name))
        return entry.remaining if entry else None

    def get_progress(self, survivor_idx: int, name: str) -> Optional[float]:
        entry = self._timers.get((survivor_idx, name))
        return entry.progress if entry else None

    def get_all_for_survivor(self, survivor_idx: int) -> dict[str, float]:
        result = {}
        for (idx, name), entry in list(self._timers.items()):
            if idx == survivor_idx:
                result[name] = entry.remaining
        return result

    def cancel_all_for_survivor(self, survivor_idx: int):
        with self._lock:
            keys = [k for k in self._timers if k[0] == survivor_idx]
            for key in keys:
                self._cancel_unsafe(key)

    def _fire(self, key: tuple):
        with self._lock:
            entry = self._timers.pop(key, None)
        if entry:
            entry.on_end()
