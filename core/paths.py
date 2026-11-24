"""
Chemins de l'application, valables en développement (python main.py) comme dans
l'exécutable PyInstaller (DBD_Assistant.exe).

  app_dir()       dossier de l'application : calibration.json y est écrit/lu
                  (dossier de l'.exe en version packagée, racine du projet sinon)
  resource_dir()  ressources embarquées (assets/...) : dossier temporaire PyInstaller
                  en version packagée, racine du projet sinon
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> str:
    return os.path.dirname(sys.executable) if is_frozen() else _ROOT


def resource_dir() -> str:
    return getattr(sys, "_MEIPASS", _ROOT)
