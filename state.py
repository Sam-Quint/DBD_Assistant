from dataclasses import dataclass, field
from typing import Optional
import threading


class SurvivorState:
    HEALTHY      = "healthy"
    INJURED      = "injured"
    DEEP_WOUNDS  = "deep_wounds"
    DOWNED       = "downed"
    CARRIED      = "carried"
    HOOKED       = "hooked"
    DEAD         = "dead"
    ESCAPED      = "escaped"
    DISCONNECTED = "disconnected"
    TRAPPED      = "trapped"

    TERMINAL = {DEAD, ESCAPED, DISCONNECTED}


@dataclass
class SurvivorData:
    state: str = SurvivorState.HEALTHY
    hook_count: int = 0

    # Perks automatiques détectées
    has_decisive_strike: bool = False
    decisive_strike_active: bool = False
    has_fardeau: bool = False
    fardeau_active: bool = False

    # Perks manuelles (liste de noms)
    manual_perks: list = field(default_factory=list)

    # Timestamps pour détection des transitions rapides
    last_state_change: float = 0.0
    last_unhook_time: Optional[float] = None

    # Snapshot des barres blanches de la frame précédente (pour Fardeau)
    prev_hook_count: int = 0


@dataclass
class GameState:
    survivors: list = field(default_factory=lambda: [SurvivorData() for _ in range(4)])
    selected_survivor: Optional[int] = None
    game_active: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def reset(self):
        with self.lock:
            self.survivors = [SurvivorData() for _ in range(4)]
            self.selected_survivor = None
            self.game_active = False


# Instance globale unique
game_state = GameState()
