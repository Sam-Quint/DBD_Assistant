import time
from core.state import game_state, SurvivorData, SurvivorState
from core.timers import TimerManager
from core.config import (
    UNHOOK_DETECTION_WINDOW,
    TIMER_DECISIVE_STRIKE,
    TIMER_FARDEAU,
    TIMER_WIGGLE,
    TIMER_WIGGLE_BONUS,
    TIMER_DEEP_WOUNDS_WINDOW,
)


class StateLogic:
    """
    Machine à états du jeu.
    Reçoit les snapshots visuels (VisionAnalyzer) et met à jour GameState.
    Détecte les transitions d'état et déclenche les timers de perks.
    """
    def __init__(self, timer_manager: TimerManager):
        self.timers = timer_manager
        self.m1_pressed_time: float = 0.0
        # Hook counts de la frame précédente (nécessaire pour détecter Fardeau)
        self._prev_hook_counts: list[int] = [0, 0, 0, 0]

    def process_snapshots(self, snapshots: list) -> None:
        """Appelé à chaque frame. Compare l'état visuel avec l'état connu et gère les transitions."""
        with game_state.lock:
            new_hook_counts = [s.hook_bars for s in snapshots]

            for i, snap in enumerate(snapshots):
                survivor = game_state.survivors[i]

                if survivor.state in SurvivorState.TERMINAL:
                    continue

                old_state = survivor.state
                new_state = snap.state

                if old_state != new_state:
                    self._handle_transition(i, survivor, old_state, new_state)

                old_bars = self._prev_hook_counts[i]
                new_bars = new_hook_counts[i]
                if new_bars != old_bars:
                    self._handle_hook_bars(i, survivor, old_bars, new_bars, new_hook_counts)

                survivor.state = new_state
                survivor.hook_count = new_hook_counts[i]

            self._prev_hook_counts = new_hook_counts

    def _handle_transition(self, idx: int, survivor: SurvivorData, old_state: str, new_state: str) -> None:
        """Gère les effets d'une transition d'état (démarrer/annuler timers, activer perks)."""
        now = time.time()

        # ── Coup Décisif ──────────────────────────────────────────────────────
        # ACCROCHÉ → BLESSÉ en < 1s = décrochage rapide par un coéquipier → CD potentiel
        if old_state == SurvivorState.HOOKED and new_state == SurvivorState.INJURED:
            if now - survivor.last_state_change < UNHOOK_DETECTION_WINDOW:
                survivor.has_decisive_strike = True
                survivor.decisive_strike_active = True
                survivor.last_unhook_time = now
                self.timers.start(idx, "decisive_strike", TIMER_DECISIVE_STRIKE,
                                  on_end=lambda i=idx: self._expire_decisive_strike(i))
            # Fenêtre Deep Wounds post-décrochage (15s) dans tous les cas
            self.timers.start(idx, "deep_wounds_window", TIMER_DEEP_WOUNDS_WINDOW,
                              on_end=lambda: None)

        # CD utilisé : PORTÉ → BLESSÉ pendant le timer = survivant a frappé le tueur
        if old_state == SurvivorState.CARRIED and new_state == SurvivorState.INJURED:
            if survivor.decisive_strike_active:
                survivor.decisive_strike_active = False
                self.timers.cancel(idx, "decisive_strike")

        # ── Wiggle ────────────────────────────────────────────────────────────
        # À TERRE → PORTÉ : démarrer le timer wiggle (16s pour se libérer)
        if old_state == SurvivorState.DOWNED and new_state == SurvivorState.CARRIED:
            self.timers.start(idx, "wiggle", TIMER_WIGGLE,
                              on_end=lambda i=idx: self._wiggle_complete(i))

        # PORTÉ → À TERRE : tueur lâche → bonus +4s sur le wiggle
        if old_state == SurvivorState.CARRIED and new_state == SurvivorState.DOWNED:
            self.timers.add_time(idx, "wiggle", TIMER_WIGGLE_BONUS)

        # PORTÉ → ACCROCHÉ : survivant accroché avant fin du wiggle → annuler
        if old_state == SurvivorState.CARRIED and new_state == SurvivorState.HOOKED:
            self.timers.cancel(idx, "wiggle")

        # ── Fardeau ───────────────────────────────────────────────────────────
        # BONNE SANTÉ → À TERRE pendant Fardeau = coup fatal absorbé → perk consommée
        if old_state == SurvivorState.HEALTHY and new_state == SurvivorState.DOWNED:
            if survivor.fardeau_active:
                survivor.fardeau_active = False
                self.timers.cancel(idx, "fardeau")

        # ── État terminal ─────────────────────────────────────────────────────
        if new_state in SurvivorState.TERMINAL:
            self.timers.cancel_all_for_survivor(idx)

        survivor.last_state_change = now

    def _handle_hook_bars(self, idx: int, survivor: SurvivorData, old_bars: int, new_bars: int, all_new: list) -> None:
        """
        Détecte Fardeau : si idx GAGNE une barre au même moment qu'un autre en PERD une
        → échange simultané = décrochage avec Fardeau.
        """
        if new_bars > old_bars:
            for j in range(4):
                if j != idx and self._prev_hook_counts[j] > all_new[j]:
                    survivor.has_fardeau = True
                    survivor.fardeau_active = True
                    self.timers.start(idx, "fardeau", TIMER_FARDEAU,
                                      on_end=lambda i=idx: self._expire_fardeau(i))
                    break

    def on_m1_pressed(self) -> None:
        """Mémorise le timestamp du dernier appui sur la touche d'attaque (pour Dead Hard V.3.0)."""
        self.m1_pressed_time = time.time()

    def reset(self) -> None:
        self._prev_hook_counts = [0, 0, 0, 0]
        self.m1_pressed_time = 0.0

    def _expire_decisive_strike(self, idx: int) -> None:
        with game_state.lock:
            game_state.survivors[idx].decisive_strike_active = False

    def _expire_fardeau(self, idx: int) -> None:
        with game_state.lock:
            game_state.survivors[idx].fardeau_active = False

    def _wiggle_complete(self, idx: int) -> None:
        pass  # La vision confirmera le passage à BLESSÉ
