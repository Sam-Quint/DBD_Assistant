from dataclasses import dataclass, field
from typing import Optional
import threading


class SurvivorState:
    """Constantes représentant tous les états visuels possibles d'un survivant."""
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

    # États terminaux : plus rien à tracker pour ce survivant
    TERMINAL = {DEAD, ESCAPED, DISCONNECTED}


@dataclass
class SurvivorData:
    """Données complètes d'un survivant : état, perks, timers, historique."""
    state: str = SurvivorState.HEALTHY
    hook_count: int = 0

    # has_ = détecté au moins une fois | active_ = timer en cours
    has_decisive_strike: bool = False
    decisive_strike_active: bool = False
    has_fardeau: bool = False
    fardeau_active: bool = False

    manual_perks: list = field(default_factory=list)

    # Timestamp du dernier changement d'état (time.time())
    last_state_change: float = 0.0
    last_unhook_time: Optional[float] = None

    # Hook count de la frame précédente (détection Fardeau)
    prev_hook_count: int = 0


@dataclass
class GameState:
    """État global de la partie, partagé entre tous les threads."""
    survivors: list = field(default_factory=lambda: [SurvivorData() for _ in range(4)])
    selected_survivor: Optional[int] = None
    game_active: bool = False
    # Verrou obligatoire avant tout accès depuis un thread non-principal
    lock: threading.Lock = field(default_factory=threading.Lock)

    def reset(self):
        """Remet tous les survivants à zéro (nouvelle partie)."""
        with self.lock:
            self.survivors = [SurvivorData() for _ in range(4)]
            self.selected_survivor = None
            self.game_active = False


# Instance unique partagée par tous les modules
game_state = GameState()
