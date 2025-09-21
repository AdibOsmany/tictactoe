import tkinter as tk
from tkinter import ttk
from .config import DIFFICULTIES
from .pages.home_page import HomePage
from .pages.game_page import GamePage
from .pages.network_page import NetworkPage

class TicTacToeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TicTacToe")
        self.resizable(False, False)

        self.mode = tk.StringVar(value="PvAI")
        self.diff_label = tk.StringVar(value="Hard")
        self.depth_limit = DIFFICULTIES[self.diff_label.get()]

        self.net = {
            "active": False,
            "is_host": False,
            "connect_client": False,  # <- new
            "host": "",
            "port": 0,
            "pin": "",
            "name": "",
            "server_proc": None,
        }

        container = ttk.Frame(self); container.grid(sticky="nsew")
        self.frames = {}
        for Page in (HomePage, GamePage, NetworkPage):
            f = Page(parent=container, controller=self)
            self.frames[Page.__name__] = f
            f.grid(row=0, column=0, sticky="nsew")

        self.show("HomePage")

    def show(self, name: str):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"): frame.on_show()

    def update_depth_from_label(self):
        self.depth_limit = DIFFICULTIES[self.diff_label.get()]
