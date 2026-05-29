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

# ── StateLogic ────────────────────────────────────────────────────────────────
# C'est le "cerveau" de l'assistant. Il reçoit les snapshots visuels produits
# par VisionAnalyzer à chaque frame et met à jour le GameState en conséquence.
#
# Son rôle principal : détecter les TRANSITIONS d'état (ex: HOOKED → INJURED)
# et déclencher les effets associés (démarrer un timer, activer une perk...).
class StateLogic:
    def __init__(self, timer_manager: TimerManager):
        self.timers = timer_manager
        self.m1_pressed_time: float = 0.0  # timestamp du dernier appui sur la touche d'attaque

        # Barres blanches (hook count) de la frame PRÉCÉDENTE.
        # Nécessaire pour détecter Fardeau : on compare frame N vs frame N-1
        # pour voir si deux survivants ont échangé une barre EN MÊME TEMPS.
        self._prev_hook_counts: list[int] = [0, 0, 0, 0]

    def process_snapshots(self, snapshots: list) -> None:
        """
        Point d'entrée principal. Appelé à chaque frame analysée (10 FPS).
        Compare l'état visuel détecté (snapshot) avec l'état connu (GameState)
        et déclenche les transitions nécessaires.
        """
        with game_state.lock:
            new_hook_counts = [s.hook_bars for s in snapshots]

            for i, snap in enumerate(snapshots):
                survivor = game_state.survivors[i]

                # Les survivants morts/sortis/déconnectés sont ignorés
                if survivor.state in SurvivorState.TERMINAL:
                    continue

                old_state = survivor.state
                new_state = snap.state

                # Si l'état a changé depuis la dernière frame → traiter la transition
                if old_state != new_state:
                    self._handle_transition(i, survivor, old_state, new_state)

                # Vérifier si les barres blanches ont changé → possible Fardeau
                old_bars = self._prev_hook_counts[i]
                new_bars = new_hook_counts[i]
                if new_bars != old_bars:
                    self._handle_hook_bars(i, survivor, old_bars, new_bars, new_hook_counts)

                # Mettre à jour l'état et le hook count dans GameState
                survivor.state = new_state
                survivor.hook_count = new_hook_counts[i]

            # Mémoriser les barres blanches de cette frame pour la prochaine
            self._prev_hook_counts = new_hook_counts

    def _handle_transition(self, idx: int, survivor: SurvivorData, old_state: str, new_state: str) -> None:
        """
        Gère les effets d'une transition d'état pour un survivant.
        Chaque bloc if correspond à une règle de détection d'une mécanique de jeu.
        """
        now = time.time()

        # ── Coup Décisif ──────────────────────────────────────────────────────
        # Règle : si un survivant passe de ACCROCHÉ → BLESSÉ en moins de 1 seconde,
        # c'est un décrochage "rapide" → un coéquipier l'a décroché → CD potentiellement actif.
        # (Un décrochage "lent" = le survivant s'est débroché seul, pas de CD.)
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
            # Dans tous les cas : démarrer la fenêtre Deep Wounds post-décrochage (15s).
            # Si le tueur frappe le survivant dans les 15s → il passe en Deep Wounds
            # au lieu de tomber à terre (mécanique du jeu indépendante de CD).
            self.timers.start(
                idx, "deep_wounds_window", TIMER_DEEP_WOUNDS_WINDOW,
                on_end=lambda: None,
            )

        # Coup Décisif utilisé : PORTÉ → BLESSÉ pendant que le timer CD est actif.
        # Le survivant a frappé le tueur pendant qu'il était porté → CD consommé.
        if old_state == SurvivorState.CARRIED and new_state == SurvivorState.INJURED:
            if survivor.decisive_strike_active:
                survivor.decisive_strike_active = False
                self.timers.cancel(idx, "decisive_strike")

        # ── Wiggle (débattement) ──────────────────────────────────────────────
        # Règle : dès qu'un survivant est porté, il peut se débattre (16s pour se libérer).
        # Le tueur ne voit pas la progression du wiggle → l'assistant la calcule.
        if old_state == SurvivorState.DOWNED and new_state == SurvivorState.CARRIED:
            self.timers.start(
                idx, "wiggle", TIMER_WIGGLE,
                on_end=lambda i=idx: self._wiggle_complete(i),
            )

        # Cas particulier : le tueur lâche le survivant (PORTÉ → À TERRE).
        # La progression du wiggle est conservée + bonus de +4 secondes fixe.
        if old_state == SurvivorState.CARRIED and new_state == SurvivorState.DOWNED:
            self.timers.add_time(idx, "wiggle", TIMER_WIGGLE_BONUS)

        # Le survivant est accroché avant la fin du wiggle → timer annulé.
        if old_state == SurvivorState.CARRIED and new_state == SurvivorState.HOOKED:
            self.timers.cancel(idx, "wiggle")

        # ── Fardeau : désactivation sur coup fatal ────────────────────────────
        # Si Fardeau est actif et que le tueur frappe le survivant en bonne santé,
        # il tombe directement à terre (BONNE SANTÉ → À TERRE) = perk consommée.
        if old_state == SurvivorState.HEALTHY and new_state == SurvivorState.DOWNED:
            if survivor.fardeau_active:
                survivor.fardeau_active = False
                self.timers.cancel(idx, "fardeau")

        # ── État terminal : nettoyer tous les timers ──────────────────────────
        # Quand un survivant meurt / sort / déconnecte, plus besoin de tracker quoi que ce soit.
        if new_state in SurvivorState.TERMINAL:
            self.timers.cancel_all_for_survivor(idx)

        # Mettre à jour le timestamp de la dernière transition
        survivor.last_state_change = now

    def _handle_hook_bars(self, idx: int, survivor: SurvivorData, old_bars: int, new_bars: int, all_new_counts: list[int]) -> None:
        """
        Détecte la perk Fardeau en observant un échange simultané de barres blanches.

        Règle : si le survivant idx GAGNE une barre (+1) au même moment qu'un AUTRE
        survivant EN PERD une (-1), c'est un décrochage avec Fardeau.
        (En temps normal sans Fardeau, seul le survivant décroché perd une barre.)
        """
        if new_bars > old_bars:
            # Ce survivant a gagné une barre → vérifier si quelqu'un en a perdu une
            for j, other in enumerate(game_state.survivors):
                if j == idx:
                    continue
                # Comparer le count précédent vs actuel pour le survivant j
                if self._prev_hook_counts[j] > all_new_counts[j]:
                    # Échange simultané détecté → Fardeau probable sur idx
                    survivor.has_fardeau = True
                    survivor.fardeau_active = True
                    self.timers.start(
                        idx, "fardeau", TIMER_FARDEAU,
                        on_end=lambda i=idx: self._expire_fardeau(i),
                    )
                    break  # un seul échange possible par frame

    def on_m1_pressed(self) -> None:
        """
        Appelé quand le joueur appuie sur la touche d'attaque du tueur.
        Utilisé pour la détection de Dead Hard (V.3.0) :
        si un survivant passe en Deep Wounds dans les 300ms suivant cette touche
        → il a utilisé Dead Hard pour absorber le coup.
        """
        self.m1_pressed_time = time.time()

    def reset(self) -> None:
        """Remet la logique à zéro (début de nouvelle partie)."""
        self._prev_hook_counts = [0, 0, 0, 0]
        self.m1_pressed_time = 0.0

    # ── Callbacks d'expiration des timers ────────────────────────────────────

    def _expire_decisive_strike(self, idx: int) -> None:
        """Les 60s de Coup Décisif sont écoulées → la perk n'est plus active."""
        with game_state.lock:
            game_state.survivors[idx].decisive_strike_active = False

    def _expire_fardeau(self, idx: int) -> None:
        """Les 40s de Fardeau sont écoulées → la vulnérabilité est terminée."""
        with game_state.lock:
            game_state.survivors[idx].fardeau_active = False

    def _wiggle_complete(self, idx: int) -> None:
        """
        Les 16s de wiggle sont écoulées → le survivant s'est libéré.
        La détection visuelle confirmera le passage à l'état BLESSÉ.
        On ne force pas l'état ici pour ne pas contredire la vision.
        """
        pass
