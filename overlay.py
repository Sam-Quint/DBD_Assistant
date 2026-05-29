import tkinter as tk
from state import game_state, SurvivorState
from timers import TimerManager
from config import PORTRAITS_ROI, MANUAL_PERK_NAMES

# ── Palette de couleurs ───────────────────────────────────────────────────────
# COLOR_BG est aussi la couleur "transparente" de la fenêtre tkinter.
# Tout pixel de cette couleur exacte devient invisible → fond du jeu visible.
# On évite le noir pur (#000000) car certains éléments du jeu sont noirs.
COLOR_BG        = "#000001"   # quasi-noir, couleur transparente de la fenêtre
COLOR_TEXT      = "#FFFFFF"
COLOR_TIMER_DS  = "#FF4444"   # rouge  → Coup Décisif
COLOR_TIMER_FAR = "#FF8800"   # orange → Fardeau
COLOR_TIMER_WIG = "#44AAFF"   # bleu   → Wiggle
COLOR_TIMER_DW  = "#FFFF00"   # jaune  → Deep Wounds window
COLOR_SELECTED  = "#FFDD00"   # jaune vif → survivant sélectionné manuellement
COLOR_HOOKED    = "#00FF88"   # vert → survivant sur le crochet

# ── Dimensions des blocs d'affichage ─────────────────────────────────────────
BLOCK_W = 200   # largeur d'un bloc survivant en pixels
BLOCK_H = 58    # hauteur d'un bloc survivant en pixels
PADDING = 2     # espacement vertical entre les blocs

# ── Définition des timers à afficher ─────────────────────────────────────────
# Chaque tuple : (clé dans TimerManager, libellé, couleur, durée totale)
# La durée totale sert à calculer le ratio de remplissage de la barre.
TIMER_DEFS = [
    ("decisive_strike",    "CD",  COLOR_TIMER_DS,  60),
    ("fardeau",            "FAR", COLOR_TIMER_FAR, 40),
    ("wiggle",             "WIG", COLOR_TIMER_WIG, 16),
    ("deep_wounds_window", "DW",  COLOR_TIMER_DW,  15),
]


# ── SurvivorFrame ─────────────────────────────────────────────────────────────
# Widget tkinter qui affiche les informations d'UN survivant :
# état, nombre de crochets, perks actives et barres de timers.
class SurvivorFrame(tk.Frame):
    def __init__(self, parent: tk.Widget, idx: int):
        super().__init__(parent, bg=COLOR_BG, width=BLOCK_W, height=BLOCK_H)
        self.idx = idx
        self.pack_propagate(False)  # forcer la taille fixe malgré le contenu
        self._build()

    def _build(self):
        """Crée tous les widgets du bloc au démarrage. Ils seront mis à jour par update()."""

        # Ligne du haut : numéro du survivant | état + crochets | perks actives
        top = tk.Frame(self, bg=COLOR_BG)
        top.pack(fill="x", padx=2, pady=(2, 0))

        # "S1", "S2", etc.
        self.lbl_num = tk.Label(
            top, text=f"S{self.idx+1}", bg=COLOR_BG, fg=COLOR_TEXT,
            font=("Consolas", 9, "bold"), width=3, anchor="w"
        )
        self.lbl_num.pack(side="left")

        # État du survivant : "SAIN ○○", "BLESSÉ ●○", "CROCHET ●●", etc.
        self.lbl_state = tk.Label(
            top, text="—", bg=COLOR_BG, fg=COLOR_TEXT,
            font=("Consolas", 9), anchor="w"
        )
        self.lbl_state.pack(side="left", padx=(2, 0))

        # Perks actives affichées à droite : "CD  FAR", "WIG", etc.
        self.lbl_perks = tk.Label(
            top, text="", bg=COLOR_BG, fg="#AAAAFF",
            font=("Consolas", 8), anchor="e"
        )
        self.lbl_perks.pack(side="right")

        # Créer une ligne de timer pour chaque mécanique (cachée par défaut)
        self.timer_bars: dict[str, tuple] = {}
        for name, label, color, _ in TIMER_DEFS:
            # Ligne complète (cachée tant que le timer est inactif)
            row = tk.Frame(self, bg=COLOR_BG)
            row.pack(fill="x", padx=2)
            row.pack_forget()  # caché → apparaît quand le timer démarre

            # Libellé court ("CD", "FAR", etc.)
            lbl = tk.Label(row, text=label, bg=COLOR_BG, fg=color,
                           font=("Consolas", 7, "bold"), width=4, anchor="w")
            lbl.pack(side="left")

            # Fond gris de la barre de progression
            bar_bg = tk.Frame(row, bg="#333333", height=6)
            bar_bg.pack(side="left", fill="x", expand=True, padx=(0, 2))
            bar_bg.pack_propagate(False)

            # Barre colorée qui se réduit en largeur au fil du temps
            # relwidth=1.0 = pleine barre, relwidth=0.0 = barre vide
            bar_fill = tk.Frame(bar_bg, bg=color, height=6)
            bar_fill.place(x=0, y=0, relwidth=1.0, height=6)

            # Secondes restantes affichées à droite de la barre
            lbl_time = tk.Label(row, text="", bg=COLOR_BG, fg=color,
                                font=("Consolas", 7), width=4, anchor="e")
            lbl_time.pack(side="right")

            self.timer_bars[name] = (row, bar_fill, lbl_time)

        # Bordure colorée du bloc (jaune = sélectionné, vert = accroché)
        self.config(highlightthickness=2, highlightbackground=COLOR_BG)

    def update(self, survivor, timers: dict, is_selected: bool):
        """Met à jour l'affichage du bloc selon l'état actuel du survivant."""

        # ── Bordure de sélection ──────────────────────────────────────────────
        # Jaune si sélectionné manuellement, vert si sur le crochet, invisible sinon.
        border_color = COLOR_SELECTED if is_selected else COLOR_BG
        if survivor.state == SurvivorState.HOOKED:
            border_color = COLOR_HOOKED
        self.config(highlightbackground=border_color)

        # ── État + crochets ───────────────────────────────────────────────────
        state_labels = {
            SurvivorState.HEALTHY:      ("SAIN",    "#FFFFFF"),
            SurvivorState.INJURED:      ("BLESSÉ",  "#FF6666"),
            SurvivorState.DEEP_WOUNDS:  ("DW",      "#FFFF44"),
            SurvivorState.DOWNED:       ("À TERRE", "#FF4444"),
            SurvivorState.CARRIED:      ("PORTÉ",   "#FF8800"),
            SurvivorState.HOOKED:       ("CROCHET", "#00FF88"),
            SurvivorState.DEAD:         ("MORT",    "#666666"),
            SurvivorState.ESCAPED:      ("SORTI",   "#44FF44"),
            SurvivorState.DISCONNECTED: ("DCO",     "#444444"),
            SurvivorState.TRAPPED:      ("PIÉGÉ",   "#FF8800"),
        }
        txt, color = state_labels.get(survivor.state, ("?", "#FFFFFF"))
        # ● = accroché, ○ = disponible (max 2 crochets avant mort)
        hooks = "●" * survivor.hook_count + "○" * (2 - min(survivor.hook_count, 2))
        self.lbl_state.config(text=f"{txt} {hooks}", fg=color)

        # ── Perks actives ─────────────────────────────────────────────────────
        perk_parts = []
        if survivor.decisive_strike_active:
            perk_parts.append("CD")
        if survivor.fardeau_active:
            perk_parts.append("FAR")
        perk_parts.extend(survivor.manual_perks)  # perks assignées manuellement
        self.lbl_perks.config(text="  ".join(perk_parts))

        # ── Barres de timers ──────────────────────────────────────────────────
        for name, label, color, total in TIMER_DEFS:
            row, bar_fill, lbl_time = self.timer_bars[name]
            remaining = timers.get(name)  # None si le timer est inactif

            if remaining is not None and remaining > 0:
                row.pack(fill="x", padx=2)  # afficher la ligne
                # Calculer la proportion de barre restante (1.0 = pleine, 0.0 = vide)
                ratio = max(0.0, min(1.0, remaining / total))
                bar_fill.place(relwidth=ratio)
                lbl_time.config(text=f"{remaining:.0f}s")
            else:
                row.pack_forget()  # cacher la ligne si timer inactif


# ── Overlay ───────────────────────────────────────────────────────────────────
# Fenêtre tkinter principale qui s'affiche par-dessus le jeu.
# Elle est transparente, sans bordure, et toujours au premier plan.
class Overlay:
    def __init__(self, timer_manager: TimerManager):
        self.timers = timer_manager
        self.root = tk.Tk()
        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        """Configure la fenêtre pour être un overlay transparent par-dessus le jeu."""
        self.root.overrideredirect(True)          # supprime la barre de titre et les bordures
        self.root.attributes("-topmost", True)    # toujours au-dessus des autres fenêtres
        self.root.attributes("-transparentcolor", COLOR_BG)  # rend COLOR_BG invisible
        self.root.attributes("-alpha", 0.92)      # légère transparence globale

        # Positionner l'overlay juste à droite de la zone des portraits
        x = PORTRAITS_ROI["x"] + PORTRAITS_ROI["w"] + 4
        y = PORTRAITS_ROI["y"]
        self.root.geometry(f"{BLOCK_W}+{x}+{y}")
        self.root.config(bg=COLOR_BG)

    def _build_ui(self):
        """Crée les 4 blocs de survivant et les empile verticalement."""
        self.survivor_frames: list[SurvivorFrame] = []
        for i in range(4):
            frame = SurvivorFrame(self.root, i)
            frame.pack(pady=PADDING)
            self.survivor_frames.append(frame)

    def update(self):
        """
        Rafraîchit l'affichage de tous les blocs.
        Appelée toutes les 100ms via root.after() (= 10 FPS d'affichage).
        tkinter n'est pas thread-safe → toutes les mises à jour UI passent par ici,
        depuis le thread principal, jamais depuis un autre thread.
        """
        with game_state.lock:
            for i, frame in enumerate(self.survivor_frames):
                survivor = game_state.survivors[i]
                timers = self.timers.get_all_for_survivor(i)
                is_selected = (game_state.selected_survivor == i)
                frame.update(survivor, timers, is_selected)
        # Reprogrammer le prochain appel dans 100ms
        self.root.after(100, self.update)

    def run(self):
        """Lance la boucle principale de tkinter (bloquante). Appelée depuis main.py."""
        self.root.after(100, self.update)
        self.root.mainloop()
