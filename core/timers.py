import threading
import time
from typing import Callable, Optional


class TimerEntry:
    """Un timer actif identifié par (survivor_idx, name)."""
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
        """0.0 (début) → 1.0 (terminé)"""
        return min(1.0, self.elapsed / self.total)


class TimerManager:
    """
    Gère tous les timers actifs du jeu.
    Chaque timer est identifié par (survivor_idx, timer_name).
    Ex : (0, "wiggle"), (2, "decisive_strike")
    """
    def __init__(self):
        self._timers: dict[tuple, TimerEntry] = {}
        self._lock = threading.Lock()

    def start(self, survivor_idx: int, name: str, duration: float, on_end: Callable):
        """Démarre un timer (annule et remplace l'éventuel timer existant du même nom)."""
        key = (survivor_idx, name)
        with self._lock:
            self._cancel_unsafe(key)
            entry = TimerEntry(duration, on_end)
            entry._thread = threading.Timer(duration, self._fire, args=[key])
            entry._thread.daemon = True
            entry._thread.start()
            self._timers[key] = entry

    def cancel(self, survivor_idx: int, name: str):
        """Annule un timer avant son expiration."""
        with self._lock:
            self._cancel_unsafe((survivor_idx, name))

    def add_time(self, survivor_idx: int, name: str, seconds: float):
        """Ajoute du temps à un timer existant (utilisé pour le bonus wiggle +4s)."""
        key = (survivor_idx, name)
        with self._lock:
            if key not in self._timers:
                return
            entry = self._timers[key]
            entry.total += seconds
            entry._thread.cancel()
            entry._thread = threading.Timer(entry.remaining, self._fire, args=[key])
            entry._thread.daemon = True
            entry._thread.start()

    def is_active(self, survivor_idx: int, name: str) -> bool:
        return (survivor_idx, name) in self._timers

    def get_remaining(self, survivor_idx: int, name: str) -> Optional[float]:
        entry = self._timers.get((survivor_idx, name))
        return entry.remaining if entry else None

    def get_all_for_survivor(self, survivor_idx: int) -> dict[str, float]:
        """Retourne {timer_name: remaining} pour un survivant. Utilisé par l'overlay."""
        return {name: e.remaining for (idx, name), e in list(self._timers.items()) if idx == survivor_idx}

    def cancel_all_for_survivor(self, survivor_idx: int):
        """Annule tous les timers d'un survivant (quand il passe en état terminal)."""
        with self._lock:
            for key in [k for k in self._timers if k[0] == survivor_idx]:
                self._cancel_unsafe(key)

    def _cancel_unsafe(self, key: tuple):
        """Annule sans acquérir le verrou (appeler depuis une section lockée)."""
        if key in self._timers:
            self._timers[key]._thread.cancel()
            del self._timers[key]

    def _fire(self, key: tuple):
        """Callback déclenché par threading.Timer à expiration."""
        with self._lock:
            entry = self._timers.pop(key, None)
        if entry:
            entry.on_end()
