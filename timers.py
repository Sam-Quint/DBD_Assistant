import threading
import time
from typing import Callable, Optional

# ── TimerEntry ────────────────────────────────────────────────────────────────
# Représente UN timer actif (ex: Coup Décisif du survivant 2).
# Stocke l'heure de départ et la durée totale pour calculer le temps restant
# à tout moment, sans avoir à mettre à jour une valeur à chaque tick.
class TimerEntry:
    def __init__(self, total: float, on_end: Callable):
        self.start_time = time.time()  # timestamp de départ (time.time())
        self.total = total             # durée totale en secondes
        self.on_end = on_end           # callback appelé quand le timer expire
        self._thread: Optional[threading.Timer] = None  # thread Python qui déclenche on_end

    @property
    def elapsed(self) -> float:
        """Temps écoulé depuis le démarrage du timer."""
        return time.time() - self.start_time

    @property
    def remaining(self) -> float:
        """Temps restant en secondes (jamais négatif)."""
        return max(0.0, self.total - self.elapsed)

    @property
    def progress(self) -> float:
        """Progression de 0.0 (début) à 1.0 (terminé). Utilisé pour les barres visuelles."""
        return min(1.0, self.elapsed / self.total)


# ── TimerManager ──────────────────────────────────────────────────────────────
# Gère tous les timers actifs du jeu.
# Chaque timer est identifié par un couple (survivor_idx, name).
# Exemples : (0, "wiggle"), (2, "decisive_strike"), (1, "fardeau")
#
# Utilise threading.Timer pour déclencher les callbacks automatiquement
# à expiration, sans avoir à "poll" à chaque frame.
class TimerManager:
    def __init__(self):
        # Dictionnaire : (survivor_idx, timer_name) → TimerEntry
        self._timers: dict[tuple, TimerEntry] = {}
        # Verrou pour protéger l'accès concurrent depuis plusieurs threads
        self._lock = threading.Lock()

    def start(self, survivor_idx: int, name: str, duration: float, on_end: Callable):
        """
        Démarre un timer. Si un timer du même nom existe déjà pour ce survivant,
        il est annulé et remplacé (évite les doublons).
        """
        key = (survivor_idx, name)
        with self._lock:
            self._cancel_unsafe(key)  # annuler l'éventuel timer précédent
            entry = TimerEntry(duration, on_end)
            # threading.Timer appelle self._fire après `duration` secondes
            entry._thread = threading.Timer(duration, self._fire, args=[key])
            entry._thread.daemon = True  # le thread ne bloque pas la fermeture du programme
            entry._thread.start()
            self._timers[key] = entry

    def cancel(self, survivor_idx: int, name: str):
        """Annule un timer actif (ex: Coup Décisif utilisé avant la fin des 60s)."""
        key = (survivor_idx, name)
        with self._lock:
            self._cancel_unsafe(key)

    def _cancel_unsafe(self, key: tuple):
        """
        Annule sans acquérir le verrou.
        À appeler UNIQUEMENT depuis une section déjà protégée par self._lock.
        """
        if key in self._timers:
            self._timers[key]._thread.cancel()  # annule le threading.Timer
            del self._timers[key]

    def add_time(self, survivor_idx: int, name: str, seconds: float):
        """
        Ajoute du temps à un timer existant.
        Utilisé pour le bonus wiggle (+4s quand le tueur lâche le survivant) :
        on rallonge simplement la durée totale et on recrée le thread.
        """
        key = (survivor_idx, name)
        with self._lock:
            if key not in self._timers:
                return  # timer inexistant → rien à faire
            entry = self._timers[key]
            entry.total += seconds
            # Recréer le thread avec le temps restant mis à jour
            entry._thread.cancel()
            remaining = entry.remaining
            entry._thread = threading.Timer(remaining, self._fire, args=[key])
            entry._thread.daemon = True
            entry._thread.start()

    def is_active(self, survivor_idx: int, name: str) -> bool:
        """Retourne True si le timer est en cours."""
        return (survivor_idx, name) in self._timers

    def get_remaining(self, survivor_idx: int, name: str) -> Optional[float]:
        """Retourne le temps restant en secondes, ou None si le timer n'existe pas."""
        entry = self._timers.get((survivor_idx, name))
        return entry.remaining if entry else None

    def get_progress(self, survivor_idx: int, name: str) -> Optional[float]:
        """Retourne la progression (0.0 à 1.0), ou None si le timer n'existe pas."""
        entry = self._timers.get((survivor_idx, name))
        return entry.progress if entry else None

    def get_all_for_survivor(self, survivor_idx: int) -> dict[str, float]:
        """
        Retourne tous les timers actifs d'un survivant sous forme de dict.
        Format : {"wiggle": 12.3, "decisive_strike": 45.0, ...}
        Utilisé par l'overlay pour savoir quoi afficher.
        """
        result = {}
        for (idx, name), entry in list(self._timers.items()):
            if idx == survivor_idx:
                result[name] = entry.remaining
        return result

    def cancel_all_for_survivor(self, survivor_idx: int):
        """
        Annule tous les timers d'un survivant.
        Appelé quand un survivant passe en état terminal (mort, sorti, déconnecté).
        """
        with self._lock:
            keys = [k for k in self._timers if k[0] == survivor_idx]
            for key in keys:
                self._cancel_unsafe(key)

    def _fire(self, key: tuple):
        """
        Callback interne déclenché par threading.Timer à expiration.
        Supprime le timer du dictionnaire et appelle le callback on_end.
        S'exécute dans le thread du timer (pas le thread principal).
        """
        with self._lock:
            entry = self._timers.pop(key, None)
        if entry:
            entry.on_end()
