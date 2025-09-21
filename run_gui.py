# run_gui.py (sits next to the tictactoe/ folder)
import os, sys, runpy

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    # Adjust MODULE depending on whether your folder is 'gui' or 'guiFolder'
    runpy.run_module("tictactoe.guiFolder.app", run_name="__main__")
    # or: runpy.run_module("tictactoe.guiFolder.app", run_name="__main__")
