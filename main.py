import threading
import time
from pynput import keyboard

from capture import ScreenCapture
from vision import VisionAnalyzer
from logic import StateLogic
from timers import TimerManager
from overlay import Overlay
from state import game_state
from config import CAPTURE_FPS, KEY_CANCEL, KEY_SELECT, KEY_PERKS, MANUAL_PERK_NAMES

# ── Architecture du programme ─────────────────────────────────────────────────
#
# Le programme tourne avec 3 threads en parallèle :
#
#   Thread principal  → overlay tkinter
#                        tkinter DOIT tourner dans le thread principal,
#                        sinon il plante. Toutes les mises à jour UI
#                        passent par root.after() pour rester dans ce thread.
#
#   Thread capture    → boucle à 10 FPS : capture → vision → logic
#                        Met à jour GameState (protégé par un verrou).
#
#   Thread clavier    → pynput listener, écoute les touches en arrière-plan.
#                        Modifie GameState (sélection de survivant, perks manuelles).
#
# La communication entre threads passe UNIQUEMENT par GameState + son verrou.


def main():
    # ── Initialisation des modules ────────────────────────────────────────────
    timer_manager = TimerManager()          # gère tous les timers (CD, Fardeau, Wiggle...)
    capture       = ScreenCapture()         # capture la zone des portraits via mss
    vision        = VisionAnalyzer()        # analyse les portraits capturés (OpenCV)
    logic         = StateLogic(timer_manager)  # machine à états + détection des perks
    overlay       = Overlay(timer_manager)  # fenêtre tkinter transparente par-dessus le jeu

    running = True

    # ── Thread de capture + analyse ───────────────────────────────────────────
    def capture_loop():
        interval = 1.0 / CAPTURE_FPS  # 0.1s entre chaque capture (10 FPS)
        while running:
            # capture() retourne None si rien n'a changé à l'écran (delta check)
            frame = capture.capture()
            if frame is not None:
                # Analyser les 4 portraits → 4 SurvivorSnapshot
                snapshots = vision.analyze_frame(frame)
                # Comparer avec l'état précédent et déclencher les effets
                logic.process_snapshots(snapshots)
            time.sleep(interval)

    capture_thread = threading.Thread(target=capture_loop, daemon=True)
    capture_thread.start()

    # ── Listener clavier ──────────────────────────────────────────────────────
    def on_press(key):
        try:
            k = key.char  # caractère de la touche (ex: "&", "é", "²"...)
        except AttributeError:
            return  # touche spéciale (F1, Ctrl, etc.) → ignorer

        # Sélection d'un survivant (touches &, é, ", ')
        # Appuyer deux fois sur la même touche désélectionne (toggle).
        if k in KEY_SELECT:
            idx = KEY_SELECT.index(k)
            with game_state.lock:
                if game_state.selected_survivor == idx:
                    game_state.selected_survivor = None  # désélectionner
                else:
                    game_state.selected_survivor = idx

        # Annuler la sélection (touche ²)
        elif k == KEY_CANCEL:
            with game_state.lock:
                game_state.selected_survivor = None

        # Assigner/retirer une perk manuelle au survivant sélectionné
        # (touches (, -, è, _, ç, à → Souplesse, Finesse, Dead Hard...)
        # Appuyer deux fois retire la perk (toggle).
        elif k in KEY_PERKS:
            perk_idx = KEY_PERKS.index(k)
            if perk_idx < len(MANUAL_PERK_NAMES):
                perk_name = MANUAL_PERK_NAMES[perk_idx]
                with game_state.lock:
                    sel = game_state.selected_survivor
                    if sel is not None:
                        survivor = game_state.survivors[sel]
                        if perk_name in survivor.manual_perks:
                            survivor.manual_perks.remove(perk_name)  # retirer
                        else:
                            survivor.manual_perks.append(perk_name)  # ajouter

        # Touche d'attaque du tueur → mémoriser le timestamp pour Dead Hard (V.3.0)
        # "m" est un placeholder : à adapter selon la touche configurée dans le jeu.
        elif k == "m":
            logic.on_m1_pressed()

    # pynput écoute TOUTES les touches clavier en arrière-plan, même quand
    # le jeu est en focus (contrairement aux raccourcis tkinter qui nécessitent
    # que la fenêtre soit active).
    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()

    print("Assistant DBD démarré. Ferme la fenêtre pour quitter.")

    # ── Lancement de l'overlay (bloquant) ────────────────────────────────────
    # overlay.run() appelle tkinter.mainloop() qui bloque jusqu'à fermeture de la fenêtre.
    # Le thread de capture continue de tourner en arrière-plan pendant ce temps.
    overlay.run()


if __name__ == "__main__":
    main()
