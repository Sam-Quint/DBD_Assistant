import time
from state import game_state, SurvivorData, SurvivorState
from timers import TimerManager
from config import (
    UNHOOK_DETECTION_WINDOW,
    TIMER_DECISIVE_STRIKE,
    TIMER_FARDEAU,
    TIMER_WIGGLE,
    TIMER_WIGGLE_BONUS,
    TIMER_DEEP_WOUNDS_WINDOW,
)


class StateLogic:
    def __init__(self, timer_manager: TimerManager):
        self.timers = timer_manager
        self.m1_pressed_time: float = 0.0
        self._prev_hook_counts: list[int] = [0, 0, 0, 0]

    def process_snapshots(self, snapshots: list) -> None:
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
        now = time.time()

        # --- Coup Décisif ---
        if old_state == SurvivorState.HOOKED and new_state == SurvivorState.INJURED:
            elapsed = now - survivor.last_state_change
            if elapsed < UNHOOK_DETECTION_WINDOW:
                survivor.has_decisive_strike = True
                survivor.decisive_strike_active = True
                survivor.last_unhook_time = now
                self.timers.start(
                    idx, "decisive_strike", TIMER_DECISIVE_STRIKE,
                    on_end=lambda i=idx: self._expire_decisive_strike(i),
                )
            # Timer Deep Wounds post-décrochage
            self.timers.start(
                idx, "deep_wounds_window", TIMER_DEEP_WOUNDS_WINDOW,
                on_end=lambda: None,
            )

        # Coup Décisif utilisé : Porté → Blessé pendant le timer
        if old_state == SurvivorState.CARRIED and new_state == SurvivorState.INJURED:
            if survivor.decisive_strike_active:
                survivor.decisive_strike_active = False
                self.timers.cancel(idx, "decisive_strike")

        # --- Wiggle ---
        if old_state == SurvivorState.DOWNED and new_state == SurvivorState.CARRIED:
            self.timers.start(
                idx, "wiggle", TIMER_WIGGLE,
                on_end=lambda i=idx: self._wiggle_complete(i),
            )

        # Tueur lâche : Porté → À terre → +4s bonus
        if old_state == SurvivorState.CARRIED and new_state == SurvivorState.DOWNED:
            self.timers.add_time(idx, "wiggle", TIMER_WIGGLE_BONUS)

        # Accroché avant fin du wiggle → reset
        if old_state == SurvivorState.CARRIED and new_state == SurvivorState.HOOKED:
            self.timers.cancel(idx, "wiggle")

        # --- Fardeau : désactivation sur coup fatal ---
        if old_state == SurvivorState.HEALTHY and new_state == SurvivorState.DOWNED:
            if survivor.fardeau_active:
                survivor.fardeau_active = False
                self.timers.cancel(idx, "fardeau")

        # État terminal → annuler tous les timers
        if new_state in SurvivorState.TERMINAL:
            self.timers.cancel_all_for_survivor(idx)

        survivor.last_state_change = now

    def _handle_hook_bars(self, idx: int, survivor: SurvivorData, old_bars: int, new_bars: int, all_new_counts: list[int]) -> None:
        if new_bars > old_bars:
            for j, other in enumerate(game_state.survivors):
                if j == idx:
                    continue
                if self._prev_hook_counts[j] > all_new_counts[j]:
                    survivor.has_fardeau = True
                    survivor.fardeau_active = True
                    self.timers.start(
                        idx, "fardeau", TIMER_FARDEAU,
                        on_end=lambda i=idx: self._expire_fardeau(i),
                    )
                    break

    def on_m1_pressed(self) -> None:
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
        pass
