import tkinter as tk
from tkinter import ttk
from ..config import DIFFICULTIES

class HomePage(ttk.Frame):
    """Landing page: choose mode (PvAI / PvP Local) + PvAI options (difficulty, role)."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.c = controller

        ttk.Label(self, text="TicTacToe", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(16, 8)
        )

        # Mode
        ttk.Label(self, text="Play Mode:").grid(row=1, column=0, sticky="w", padx=(16,8), pady=4)
        self.mode_box = ttk.Combobox(self, state="readonly", width=12,
                                     textvariable=self.c.mode, values=["PvAI", "PvP Local"])
        self.mode_box.grid(row=1, column=1, sticky="w", padx=(0,16), pady=4)
        self.mode_box.bind("<<ComboboxSelected>>", lambda _e: self._apply_enablement())

        # PvAI options
        ttk.Label(self, text="Difficulty:").grid(row=2, column=0, sticky="w", padx=(16,8), pady=4)
        self.diff_box = ttk.Combobox(self, state="readonly", width=8,
                                     textvariable=self.c.diff_label, values=list(DIFFICULTIES.keys()))
        self.diff_box.grid(row=2, column=1, sticky="w", padx=(0,16), pady=4)
        self.diff_box.bind("<<ComboboxSelected>>", lambda _e: self.c.update_depth_from_label())

        ttk.Button(self, text="Start Game", command=lambda: self.c.show("GamePage")).grid(
            row=4, column=0, columnspan=3, pady=(12, 16), ipadx=12
        )

        # inside HomePage.__init__(), after the "Start Game" button:
        ttk.Button(self, text="Multiplayer Online", command=lambda: self.c.show("NetworkPage")).grid(
            row=6, column=0, columnspan=3, pady=(0, 12), ipadx=12
        )


        ttk.Label(self, text="Tip: PvP Local = two players taking turns on this board.\n"
                             "PvAI = you vs computer (Easy/Medium/Hard).").grid(
            row=5, column=0, columnspan=3, pady=(0, 12)
        )

        self._apply_enablement()

    def on_show(self):
        self._apply_enablement()

    def _apply_enablement(self):
        is_pvai = (self.c.mode.get() == "PvAI")
        self.diff_box.configure(state="readonly" if is_pvai else "disabled")
