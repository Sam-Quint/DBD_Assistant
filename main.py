"""
Assistant DBD — Point d'entrée

Architecture :
  Thread principal → overlay tkinter (doit rester dans le thread principal)
  Thread capture   → capture + vision + logic à 10 FPS
  Thread clavier   → pynput listener (écoute toutes les touches)

Communication entre threads : GameState partagé (protégé par un verrou).
"""
import os
import sys
import threading
import time

# Python embarqué (python\) : le dossier du projet n'est pas dans le chemin d'import par défaut
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pynput import keyboard

from vision.capture import ScreenCapture
from vision.analyzer import VisionAnalyzer
from core.logic import StateLogic
from core.timers import TimerManager
from ui.overlay import Overlay
from core.state import game_state
from core.config import CAPTURE_FPS, KEY_CANCEL, KEY_SELECT, KEY_PERKS, MANUAL_PERK_NAMES


def main():
    # DBD_Assistant.exe --calibrer : réglage automatique des portraits (menu console)
    if "--calibrer" in sys.argv:
        from tools import auto_calibrer
        auto_calibrer.main()
        return

    timer_manager = TimerManager()
    capture       = ScreenCapture()
    vision        = VisionAnalyzer()
    logic         = StateLogic(timer_manager)
    overlay       = Overlay(timer_manager)

    running = True

    # ── Thread capture ────────────────────────────────────────────────────────
    def capture_loop():
        interval = 1.0 / CAPTURE_FPS
        while running:
            frame = capture.capture()  # None si rien n'a changé à l'écran
            if frame is not None:
                snapshots = vision.analyze_frame(frame)
                logic.process_snapshots(snapshots)
            time.sleep(interval)

    threading.Thread(target=capture_loop, daemon=True).start()

    # ── Thread clavier ────────────────────────────────────────────────────────
    def on_press(key):
        try:
            k = key.char
        except AttributeError:
            return

        # Sélectionner un survivant (toggle : appuyer deux fois désélectionne)
        if k in KEY_SELECT:
            idx = KEY_SELECT.index(k)
            with game_state.lock:
                game_state.selected_survivor = None if game_state.selected_survivor == idx else idx

        # Annuler la sélection
        elif k == KEY_CANCEL:
            with game_state.lock:
                game_state.selected_survivor = None

        # Assigner / retirer une perk manuelle au survivant sélectionné (toggle)
        elif k in KEY_PERKS:
            perk_idx = KEY_PERKS.index(k)
            if perk_idx < len(MANUAL_PERK_NAMES):
                perk_name = MANUAL_PERK_NAMES[perk_idx]
                with game_state.lock:
                    sel = game_state.selected_survivor
                    if sel is not None:
                        perks = game_state.survivors[sel].manual_perks
                        if perk_name in perks:
                            perks.remove(perk_name)
                        else:
                            perks.append(perk_name)

        # Touche d'attaque (placeholder "m" — adapter selon le setup du joueur)
        elif k == "m":
            logic.on_m1_pressed()

    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()

    print("Assistant DBD démarré. Ferme la fenêtre pour quitter.")
    overlay.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        if getattr(sys, "frozen", False):   # exécutable : garder la fenêtre ouverte pour lire l'erreur
            input("Appuie sur Entrée pour fermer...")
        raise SystemExit(1)
