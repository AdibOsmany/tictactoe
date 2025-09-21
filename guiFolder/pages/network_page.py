# tictactoe/gui/pages/network_page.py
import sys, socket, subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, font
from ...discover import discover_lan

def first_free_port(start=49152, end=65535, host="0.0.0.0") -> int | None:
    """Return first available TCP port in [start, end], or None if none found."""
    for p in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, p))
            except OSError:
                continue
            return p
    return None

class NetworkPage(ttk.Frame):
    """
    Multiplayer page with two buttons:
      - Host: launch server, connect GUI as host player
      - Join: scan LAN, display available hosts as clickable buttons
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.c = controller

        ttk.Label(self, text="Multiplayer", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(16, 12)
        )

        ttk.Button(self, text="Host", command=self._host).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 12), ipadx=12
        )
        ttk.Button(self, text="Join", command=self._join).grid(
            row=1, column=1, sticky="ew", padx=16, pady=(0, 12), ipadx=12
        )

        ttk.Separator(self, orient="horizontal").grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 8)
        )
        ttk.Button(self, text="← Back", command=lambda: self.c.show("HomePage")).grid(
            row=3, column=0, columnspan=2, pady=(0, 16)
        )

    # ---------------- Host flow ----------------
    def _host(self):
        name = simpledialog.askstring("Your Name", "Enter your display name:", parent=self)
        if not name: return
        pin = simpledialog.askstring("Set PIN", "Enter a game PIN:", show="•", parent=self)
        if not pin: return

        port = first_free_port()
        if not port:
            messagebox.showerror("No Ports", "Couldn't find a free port to host on.")
            return

        try:
            self.c.net["server_proc"] = subprocess.Popen(
                [sys.executable, "-m", "tictactoe.server_net",
                 "--host", "0.0.0.0", "--port", str(port), "--pin", pin, "--host-name", name], 
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception as e:
            messagebox.showerror("Host Error", f"Failed to start server:\n{e}")
            return

        self.c.net.update({
            "active": True,
            "is_host": True,
            "connect_client": True,
            "host": "127.0.0.1",
            "port": port,
            "pin": pin,
            "name": name.strip(),
        })
        self.c.show("GamePage")


# ---------------- Join flow ----------------
    def _join(self):
        try:
            servers = discover_lan(timeout=2.0)
        except Exception as e:
            messagebox.showerror("Scan Failed", str(e)); return

        if not servers:
            messagebox.showinfo("No Hosts", "No LAN hosts found."); return

        # Build popup
        popup = tk.Toplevel(self)
        popup.title("Select Host")
        popup.resizable(False, False)

        ttk.Label(popup, text="Available Games", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, padx=12, pady=(12, 8)
        )

        bold_font = font.nametofont("TkDefaultFont").copy()
        bold_font.configure(weight="bold")

        for i, s in enumerate(servers):
            frame = ttk.Frame(popup)
            frame.grid(row=i+1, column=0, sticky="ew", padx=12, pady=4)

            # "Join "
            ttk.Label(frame, text="Play against ").pack(side="left")

            # host name (bold)
            host_name = s.get("name", "Players")
            ttk.Label(frame, text=host_name, font=bold_font).pack(side="left")


            # Join button at the end
            join_btn = ttk.Button(
                frame,
                text="▶",
                command=lambda s=s, win=popup: self._select_host(s, win)
            )
            join_btn.pack(side="right")

        ttk.Button(popup, text="Cancel", command=popup.destroy).grid(
            row=len(servers)+1, column=0, pady=(8,12)
        )


    def _select_host(self, server_info: dict, win: tk.Toplevel):
        win.destroy()

        # Ask player for their display name
        name = simpledialog.askstring("Your Name", "Enter your display name:", parent=self)
        if not name: return

        pin = simpledialog.askstring("PIN", "Enter host's PIN:", show="•", parent=self)
        if not pin: return

        self.c.net.update({
            "active": True,
            "is_host": False,
            "connect_client": True,
            "host": server_info["ip"],
            "port": int(server_info["port"]),
            "pin": pin.strip(),
            "name": name.strip(),
            "server_proc": None,
        })
        self.c.show("GamePage")
