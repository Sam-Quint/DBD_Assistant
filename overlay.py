import tkinter as tk
from state import game_state, SurvivorState
from timers import TimerManager
from config import PORTRAITS_ROI, MANUAL_PERK_NAMES

COLOR_BG        = "#000001"
COLOR_TEXT      = "#FFFFFF"
COLOR_TIMER_DS  = "#FF4444"
COLOR_TIMER_FAR = "#FF8800"
COLOR_TIMER_WIG = "#44AAFF"
COLOR_TIMER_DW  = "#FFFF00"
COLOR_SELECTED  = "#FFDD00"
COLOR_HOOKED    = "#00FF88"

BLOCK_W = 200
BLOCK_H = 58
PADDING = 2

TIMER_DEFS = [
    ("decisive_strike",   "CD",  COLOR_TIMER_DS,  60),
    ("fardeau",           "FAR", COLOR_TIMER_FAR, 40),
    ("wiggle",            "WIG", COLOR_TIMER_WIG, 16),
    ("deep_wounds_window","DW",  COLOR_TIMER_DW,  15),
]


class SurvivorFrame(tk.Frame):
    def __init__(self, parent: tk.Widget, idx: int):
        super().__init__(parent, bg=COLOR_BG, width=BLOCK_W, height=BLOCK_H)
        self.idx = idx
        self.pack_propagate(False)
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=COLOR_BG)
        top.pack(fill="x", padx=2, pady=(2, 0))

        self.lbl_num = tk.Label(
            top, text=f"S{self.idx+1}", bg=COLOR_BG, fg=COLOR_TEXT,
            font=("Consolas", 9, "bold"), width=3, anchor="w"
        )
        self.lbl_num.pack(side="left")

        self.lbl_state = tk.Label(
            top, text="—", bg=COLOR_BG, fg=COLOR_TEXT,
            font=("Consolas", 9), anchor="w"
        )
        self.lbl_state.pack(side="left", padx=(2, 0))

        self.lbl_perks = tk.Label(
            top, text="", bg=COLOR_BG, fg="#AAAAFF",
            font=("Consolas", 8), anchor="e"
        )
        self.lbl_perks.pack(side="right")

        self.timer_bars: dict[str, tuple] = {}
        for name, label, color, _ in TIMER_DEFS:
            row = tk.Frame(self, bg=COLOR_BG)
            row.pack(fill="x", padx=2)
            row.pack_forget()

            lbl = tk.Label(row, text=label, bg=COLOR_BG, fg=color,
                           font=("Consolas", 7, "bold"), width=4, anchor="w")
            lbl.pack(side="left")

            bar_bg = tk.Frame(row, bg="#333333", height=6)
            bar_bg.pack(side="left", fill="x", expand=True, padx=(0, 2))
            bar_bg.pack_propagate(False)

            bar_fill = tk.Frame(bar_bg, bg=color, height=6)
            bar_fill.place(x=0, y=0, relwidth=1.0, height=6)

            lbl_time = tk.Label(row, text="", bg=COLOR_BG, fg=color,
                                font=("Consolas", 7), width=4, anchor="e")
            lbl_time.pack(side="right")

            self.timer_bars[name] = (row, bar_fill, lbl_time)

        self.config(highlightthickness=2, highlightbackground=COLOR_BG)

    def update(self, survivor, timers: dict, is_selected: bool):
        border_color = COLOR_SELECTED if is_selected else COLOR_BG
        if survivor.state == SurvivorState.HOOKED:
            border_color = COLOR_HOOKED
        self.config(highlightbackground=border_color)

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
        hooks = "●" * survivor.hook_count + "○" * (2 - min(survivor.hook_count, 2))
        self.lbl_state.config(text=f"{txt} {hooks}", fg=color)

        perk_parts = []
        if survivor.decisive_strike_active:
            perk_parts.append("CD")
        if survivor.fardeau_active:
            perk_parts.append("FAR")
        perk_parts.extend(survivor.manual_perks)
        self.lbl_perks.config(text="  ".join(perk_parts))

        for name, label, color, total in TIMER_DEFS:
            row, bar_fill, lbl_time = self.timer_bars[name]
            remaining = timers.get(name)

            if remaining is not None and remaining > 0:
                row.pack(fill="x", padx=2)
                ratio = max(0.0, min(1.0, remaining / total))
                bar_fill.place(relwidth=ratio)
                lbl_time.config(text=f"{remaining:.0f}s")
            else:
                row.pack_forget()


class Overlay:
    def __init__(self, timer_manager: TimerManager):
        self.timers = timer_manager
        self.root = tk.Tk()
        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", COLOR_BG)
        self.root.attributes("-alpha", 0.92)
        x = PORTRAITS_ROI["x"] + PORTRAITS_ROI["w"] + 4
        y = PORTRAITS_ROI["y"]
        self.root.geometry(f"{BLOCK_W}+{x}+{y}")
        self.root.config(bg=COLOR_BG)

    def _build_ui(self):
        self.survivor_frames: list[SurvivorFrame] = []
        for i in range(4):
            frame = SurvivorFrame(self.root, i)
            frame.pack(pady=PADDING)
            self.survivor_frames.append(frame)

    def update(self):
        with game_state.lock:
            for i, frame in enumerate(self.survivor_frames):
                survivor = game_state.survivors[i]
                timers = self.timers.get_all_for_survivor(i)
                is_selected = (game_state.selected_survivor == i)
                frame.update(survivor, timers, is_selected)
        self.root.after(100, self.update)

    def run(self):
        self.root.after(100, self.update)
        self.root.mainloop()
