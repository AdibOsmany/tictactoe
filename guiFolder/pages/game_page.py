import tkinter as tk
from tkinter import ttk, messagebox
import threading, asyncio, json, time
from ...game import Game
from ...ai import best_move
from ..config import CELL, PAD, GRID, DIFFICULTIES

# ---------- Minimal embedded async client for network play ----------
ENC = "utf-8"

def _dumps(obj: dict) -> bytes:
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode(ENC)

async def _read_json_line(reader: asyncio.StreamReader):
    line = await reader.readline()
    if not line:
        return None
    try:
        return json.loads(line.decode(ENC))
    except json.JSONDecodeError:
        return {"type": "error", "error": "bad_json"}

class NetClient:
    def __init__(self, host: str, port: int, name: str, pin: str, on_event):
        self.host, self.port, self.name, self.pin = host, port, name, pin
        self.on_event = on_event
        self.loop = None
        self.reader = None
        self.writer = None
        self.thread = None
        self._stopping = False

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._amain())

    async def _amain(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.writer.write(_dumps({"type": "hello", "name": self.name, "pin": self.pin}))
            await self.writer.drain()
            while True:
                msg = await _read_json_line(self.reader)
                if msg is None:
                    self.on_event({"type": "_disconnect"})
                    return
                self.on_event(msg)
        except Exception as e:
            self.on_event({"type": "_error", "error": str(e)})

    def send_move(self, idx: int):
        if not self.writer or not self.loop:
            return
        try:
            self.writer.write(_dumps({"type": "move", "idx": idx}))
            asyncio.run_coroutine_threadsafe(self.writer.drain(), self.loop)
        except Exception:
            pass

    def quit(self):
        """Polite quit then hard close."""
        self._shutdown(send_quit=True)

    def close(self):
        """Hard close without sending (used after receiving 'end'/_disconnect)."""
        self._shutdown(send_quit=False)

    def _shutdown(self, send_quit: bool):
        if self._stopping:
            return
        self._stopping = True
        try:
            if send_quit and self.writer and self.loop and not self.writer.is_closing():
                self.writer.write(_dumps({"type": "quit"}))
                asyncio.run_coroutine_threadsafe(self.writer.drain(), self.loop)
        except Exception:
            pass
        try:
            if self.writer and not self.writer.is_closing():
                self.writer.close()
        except Exception:
            pass
        try:
            if self.loop:
                self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass
        try:
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1.0)
        except Exception:
            pass

# ---------- Game Page ----------
class GamePage(ttk.Frame):
    """PvAI, PvP Local, or Network (LAN).
       - LAN: only an Exit button (returns Home). Window X quits entire app.
       - Hard disconnects so guest leaves cleanly and server session ends."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.c = controller

        # Header
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 0))
        header.columnconfigure(0, weight=1)
        self.title_lbl = ttk.Label(header, text="", font=("Segoe UI", 12, "bold"))
        self.title_lbl.grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="← Exit", command=self._exit_to_home).grid(row=0, column=1, sticky="e")

        # Canvas
        self.canvas = tk.Canvas(self, width=GRID*CELL, height=GRID*CELL, bg="white", highlightthickness=0)
        self.canvas.grid(row=1, column=0, padx=PAD, pady=(PAD, 0))
        self.canvas.bind("<Button-1>", self.on_click)

        # Footer
        bottom = ttk.Frame(self)
        bottom.grid(row=2, column=0, sticky="ew", padx=PAD, pady=(4, PAD))
        bottom.columnconfigure(0, weight=1)
        self.status = ttk.Label(bottom, text="", anchor="w")
        self.status.grid(row=0, column=0, sticky="w")

        # Buttons
        self.new_btn = ttk.Button(bottom, text="New Game", command=self.reset_game)
        self.new_btn.grid(row=0, column=1, sticky="e")

        # State
        self.g = None
        self.ai_mark = None
        self.last_move_cell = None

        # Network helpers
        self.is_network = False
        self.net_client: NetClient | None = None

        self._ended = False

        self._toplevel = None

    # ---------- Lifecycle ----------
    def on_show(self):
        self._toplevel = self.winfo_toplevel()
        self._toplevel.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.reset_game(full_refresh_title=True)

    def reset_game(self, full_refresh_title: bool = False):
        self._ended = False
        self.last_move_cell = None
        self.is_network = bool(self.c.net.get("active"))

        if self.is_network:
            self.new_btn.grid_remove()
        else:
            self.new_btn.grid()

        if self.is_network:
            # Network mode
            self.g = Game.new()
            self.ai_mark = None

            if full_refresh_title:
                role = "Host" if self.c.net.get("is_host") else "Guest"
                pname = (self.c.net.get("name") or "").strip() or role
                self.title_lbl.config(text=f"Welcome {pname} ({role})")

            self.draw()

            if self.c.net.get("connect_client"):
                self.update_status("Connecting…")
                if not self.net_client:
                    self.net_client = NetClient(
                        host=self.c.net["host"],
                        port=self.c.net["port"],
                        name=self.c.net.get("name") or ("LocalPlayer" if self.c.net.get("is_host") else "GuestPlayer"),
                        pin=self.c.net["pin"],
                        on_event=self._net_event
                    )
                    self.net_client.start()
            else:
                self.update_status("Waiting for opponent… (host is seated)")
        else:
            # Local modes
            self.g = Game.new()
            if self.c.mode.get() == "PvAI":
                self.ai_mark = "O"  # human is X
            else:
                self.ai_mark = None

            if full_refresh_title:
                if self.c.mode.get() == "PvAI":
                    self.title_lbl.config(text=f"PvAI — You: X | Difficulty: {self.c.diff_label.get()}")
                else:
                    self.title_lbl.config(text="PvP Local — Two players on one board")

            self.draw()
            self.update_status()

            if self.c.mode.get() == "PvAI" and self.g.turn == self.ai_mark:
                self.after(150, self.ai_reply)

    # ---------- Drawing ----------
    def draw(self):
        c = self.canvas
        c.delete("all")
        # grid
        for i in range(1, GRID):
            c.create_line(i*CELL, 0, i*CELL, GRID*CELL, width=2)
            c.create_line(0, i*CELL, GRID*CELL, i*CELL, width=2)
        # highlight
        if self.last_move_cell is not None:
            r, col = self.last_move_cell
            x0, y0 = col*CELL, r*CELL
            x1, y1 = x0 + CELL, y0 + CELL
            c.create_rectangle(x0+2, y0+2, x1-2, y1-2, outline="#4a90e2", width=3)
        # marks / hints
        for i, mark in enumerate(self.g.board):
            x = (i % GRID) * CELL
            y = (i // GRID) * CELL
            if mark == "X":
                c.create_line(x+15, y+15, x+CELL-15, y+CELL-15, width=3)
                c.create_line(x+CELL-15, y+15, x+15, y+CELL-15, width=3)
            elif mark == "O":
                c.create_oval(x+15, y+15, x+CELL-15, y+CELL-15, width=3)
            else:
                c.create_text(x + CELL//2, y + CELL//2, text=str(i+1), fill="#cccccc", font=("Arial", 18))

    # ---------- Status ----------
    def update_status(self, msg=None):
        if msg:
            self.status.config(text=msg)
            return
        if self.g.terminal():
            w = self.g.winner()
            self.status.config(text=f"Game Over — Winner: {w if w else 'Draw'}")
            return
        if self.is_network:
            self.status.config(text=f"Network — {self.g.turn}'s turn.")
        elif self.c.mode.get() == "PvAI":
            if self.g.turn == self.ai_mark:
                self.status.config(text=f"AI (O) thinking… [{self.c.diff_label.get()}]")
            else:
                self.status.config(text="Your turn (X). Click a square (1–9).")
        else:
            self.status.config(text=f"PvP Local — {self.g.turn}'s turn. Click a square (1–9).")

    # ---------- Input ----------
    def on_click(self, event):
        if self.g.terminal():
            return
        col = event.x // CELL
        row = event.y // CELL
        idx = row * GRID + col + 1  # 1-based

        if self.is_network:
            if self.net_client:
                self.net_client.send_move(idx)
        elif self.c.mode.get() == "PvAI":
            if self.g.turn == self.ai_mark:
                return
            if self.g.play(idx):
                self.last_move_cell = (row, col)
                self.draw(); self.update_status()
                self.after(120, self._maybe_ai)
        else:
            # PvP Local
            if self.g.play(idx):
                self.last_move_cell = (row, col)
                self.draw(); self.update_status()

    def _maybe_ai(self):
        if self.g.terminal():
            self.finish(); return
        if self.g.turn == self.ai_mark:
            self.ai_reply()

    def ai_reply(self):
        if self.g.terminal():
            self.finish(); return
        depth = DIFFICULTIES[self.c.diff_label.get()]
        idx, _ = best_move(self.g, as_player=self.ai_mark, depth_limit=depth)
        zero = idx - 1
        row, col = zero // GRID, zero % GRID
        self.g.play(idx)
        self.last_move_cell = (row, col)
        self.draw()
        if self.g.terminal():
            self.finish()
        else:
            self.update_status()

    def finish(self):
        """Always show popup. In LAN, after OK we return Home (not app quit)."""
        if self._ended:
            return
        self._ended = True
        w = self.g.winner()
        messagebox.showinfo("Game Over", f"Winner: {w if w else 'Draw'}")
        if self.is_network:
            self._exit_to_home()
        else:
            self.update_status()

    # ---------- Exit behaviors ----------
    def _exit_to_home(self):
        """Exit button: end the match and return to HomePage (keep app open)."""
        if self.is_network and not self._ended:
            if not messagebox.askyesno("Leave Match", "Return to Home and end the match for both players?"):
                return

        if self.is_network and self.net_client:
            try:
                self.net_client.quit()  
            except Exception:
                pass

        sp = self.c.net.get("server_proc")
        if self.is_network and self.c.net.get("is_host") and sp:
            try:
                if sp.poll() is None:
                    sp.terminate()
                    for _ in range(10):
                        if sp.poll() is not None:
                            break
                        time.sleep(0.05)
                    if sp.poll() is None:
                        sp.kill()
            except Exception:
                pass
            finally:
                self.c.net["server_proc"] = None

        self.net_client = None
        if self.is_network:
            self.c.net["active"] = False

        self.c.show("HomePage")

    def _on_window_close(self):
        """Top-right X button: confirm and quit whole app after teardown."""
        prompt = "Exit the game?"
        if not messagebox.askyesno("Exit Game", prompt):
            return

        if self.is_network and self.net_client:
            try:
                self.net_client.quit()
            except Exception:
                pass

        sp = self.c.net.get("server_proc")
        if self.is_network and self.c.net.get("is_host") and sp:
            try:
                if sp.poll() is None:
                    sp.terminate()
                    for _ in range(10):
                        if sp.poll() is not None:
                            break
                        time.sleep(0.05)
                    if sp.poll() is None:
                        sp.kill()
            except Exception:
                pass
            finally:
                self.c.net["server_proc"] = None

        self.net_client = None
        if self.is_network:
            self.c.net["active"] = False

        self.winfo_toplevel().destroy()

    # ---------- Network event handling ----------
    def _net_event(self, msg: dict):
        self.after(0, lambda m=msg: self._handle_net_event_main(m))

    def _handle_net_event_main(self, msg: dict):
        t = msg.get("type")
        if t in ("hello", "status") and msg.get("status") == "waiting_for_opponent":
            self.update_status("Waiting for opponent…")
        elif msg.get("status") == "matched" or t == "hello":
            you = msg.get("you")
            opp = msg.get("opponent")
            if you or opp:
                self.update_status(f"Matched: you={you} vs {opp}")
        elif t == "state":
            board = msg.get("board", [" "] * 9)
            self.g.board = board[:]
            self.g.turn = msg.get("turn", "X")
            self.draw()
            if msg.get("terminal"):
                self.finish()
            else:
                self.update_status()
        elif t == "your_turn":
            self.update_status("Your turn — click a square (1–9).")
        elif t == "end":
            if self.is_network and self.net_client:
                try:
                    self.net_client.close()
                except Exception:
                    pass
                self.net_client = None
            if not self._ended:
                reason = msg.get("reason", "opponent_quit").replace("_", " ").title()
                messagebox.showinfo("Match Ended", reason)
                self._ended = True
            self._exit_to_home()
        elif t == "_disconnect":
            if self.is_network and self.net_client:
                try:
                    self.net_client.close()
                except Exception:
                    pass
                self.net_client = None
            if not self._ended:
                self._ended = True
            self._exit_to_home()
        elif t in ("error", "_error"):
            self.update_status("Network error: " + str(msg.get("error")))
