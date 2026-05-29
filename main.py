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


def main():
    timer_manager = TimerManager()
    capture = ScreenCapture()
    vision = VisionAnalyzer()
    logic = StateLogic(timer_manager)
    overlay = Overlay(timer_manager)

    running = True

    def capture_loop():
        interval = 1.0 / CAPTURE_FPS
        while running:
            frame = capture.capture()
            if frame is not None:
                snapshots = vision.analyze_frame(frame)
                logic.process_snapshots(snapshots)
            time.sleep(interval)

    capture_thread = threading.Thread(target=capture_loop, daemon=True)
    capture_thread.start()

    def on_press(key):
        try:
            k = key.char
        except AttributeError:
            return

        if k in KEY_SELECT:
            idx = KEY_SELECT.index(k)
            with game_state.lock:
                if game_state.selected_survivor == idx:
                    game_state.selected_survivor = None
                else:
                    game_state.selected_survivor = idx

        elif k == KEY_CANCEL:
            with game_state.lock:
                game_state.selected_survivor = None

        elif k in KEY_PERKS:
            perk_idx = KEY_PERKS.index(k)
            if perk_idx < len(MANUAL_PERK_NAMES):
                perk_name = MANUAL_PERK_NAMES[perk_idx]
                with game_state.lock:
                    sel = game_state.selected_survivor
                    if sel is not None:
                        survivor = game_state.survivors[sel]
                        if perk_name in survivor.manual_perks:
                            survivor.manual_perks.remove(perk_name)
                        else:
                            survivor.manual_perks.append(perk_name)

        # Touche d'attaque du tueur (placeholder — adapter selon setup)
        elif k == "m":
            logic.on_m1_pressed()

    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()

    print("Assistant DBD démarré. Ferme la fenêtre pour quitter.")
    overlay.run()


if __name__ == "__main__":
    main()
