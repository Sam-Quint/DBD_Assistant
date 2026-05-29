from dataclasses import dataclass, field
from typing import Optional
import threading

# ── États possibles d'un survivant ───────────────────────────────────────────
# Ces constantes sont utilisées partout dans le projet pour comparer les états.
# On utilise une classe plutôt qu'un enum pour pouvoir faire des comparaisons
# simples avec des strings (ex: survivor.state == SurvivorState.HOOKED).
class SurvivorState:
    HEALTHY      = "healthy"       # Bonne santé, portrait normal
    INJURED      = "injured"       # Blessé, griffures rouges sur le portrait
    DEEP_WOUNDS  = "deep_wounds"   # Blessé + Deep Wounds, barre jaune visible
    DOWNED       = "downed"        # À terre, silhouette allongée + barre rouge
    CARRIED      = "carried"       # Porté par le tueur
    HOOKED       = "hooked"        # Accroché, symbole crochet + barre rouge
    DEAD         = "dead"          # Mort / Sacrifié / Bleed Out
    ESCAPED      = "escaped"       # Sorti par la porte
    DISCONNECTED = "disconnected"  # Déconnecté en cours de partie
    TRAPPED      = "trapped"       # Pris dans un piège (tueur Trappeur uniquement)

    # États terminaux : une fois dans cet état, le survivant est ignoré.
    # Plus besoin de tracker ses timers ou transitions.
    TERMINAL = {DEAD, ESCAPED, DISCONNECTED}


# ── Données d'un survivant ────────────────────────────────────────────────────
# Un objet SurvivorData est créé pour chacun des 4 survivants au début de la partie.
# Il est mis à jour à chaque frame par logic.py.
@dataclass
class SurvivorData:
    state: str = SurvivorState.HEALTHY
    hook_count: int = 0  # Nombre de fois accroché (0, 1 ou 2 barres blanches)

    # Coup Décisif :
    # has_ = la perk a été détectée au moins une fois sur ce survivant
    # active_ = le timer est actuellement en cours (60s)
    has_decisive_strike: bool = False
    decisive_strike_active: bool = False

    # Fardeau : même logique que Coup Décisif
    has_fardeau: bool = False
    fardeau_active: bool = False

    # Perks attribuées manuellement par le joueur via les touches clavier
    manual_perks: list = field(default_factory=list)

    # Timestamp du dernier changement d'état (time.time()).
    # Utilisé pour calculer si un décrochage a été "rapide" (< 1s → Coup Décisif).
    last_state_change: float = 0.0
    last_unhook_time: Optional[float] = None

    # Nombre de barres blanches à la frame PRÉCÉDENTE.
    # Nécessaire pour détecter Fardeau : on compare l'état actuel vs précédent
    # pour voir si deux survivants ont échangé une barre simultanément.
    prev_hook_count: int = 0


# ── État global de la partie ──────────────────────────────────────────────────
# Un seul objet GameState existe dans tout le programme (instance globale).
# Il est partagé entre les threads (capture, logic, overlay) via un verrou.
@dataclass
class GameState:
    survivors: list = field(default_factory=lambda: [SurvivorData() for _ in range(4)])

    # Index du survivant actuellement sélectionné manuellement (0-3), ou None
    selected_survivor: Optional[int] = None

    game_active: bool = False

    # Verrou threading : OBLIGATOIRE avant toute lecture ou écriture de GameState
    # depuis un thread autre que le thread principal.
    # Usage : with game_state.lock: ...
    lock: threading.Lock = field(default_factory=threading.Lock)

    def reset(self):
        """Remet tous les survivants à zéro (début de nouvelle partie)."""
        with self.lock:
            self.survivors = [SurvivorData() for _ in range(4)]
            self.selected_survivor = None
            self.game_active = False


# Instance globale unique, importée par tous les modules qui en ont besoin.
game_state = GameState()
