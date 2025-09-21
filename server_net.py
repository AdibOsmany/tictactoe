import asyncio, argparse, logging, json, socket, threading
from .game import Game  # uses 1–9 indexing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

DISCOVERY_MAGIC = b"TTT_DISCOVER_V1"
DISCOVERY_ENCODING = "utf-8"

def _udp_discovery_responder_loop(listen_ip: str, dport: int, name: str, game_port: int, pin_required: bool):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((listen_ip, dport))
        logging.info(f"UDP discovery responder on {listen_ip}:{dport}")
    except Exception as e:
        logging.warning(f"UDP discovery bind failed on {dport}: {e}")
        sock.close()
        return
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if data.strip() == DISCOVERY_MAGIC:
                payload = {
                    "service": "tictactoe",
                    "proto": 1,
                    "name": name,
                    "port": game_port,
                    "pin_required": bool(pin_required),
                }
                sock.sendto(json.dumps(payload).encode(DISCOVERY_ENCODING), addr)
        except Exception:
            continue

def start_udp_discovery_responder(listen_ip: str, dport: int, name: str, game_port: int, pin_required: bool):
    t = threading.Thread(
        target=_udp_discovery_responder_loop,
        args=(listen_ip, dport, name, game_port, pin_required),
        daemon=True,
    )
    t.start()
    return t

# ---- helpers ----
ENC = "utf-8"
def dumps(obj) -> bytes:
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode(ENC)

async def read_json_line(reader: asyncio.StreamReader):
    line = await reader.readline()
    if not line:
        return None
    try:
        return json.loads(line.decode(ENC))
    except json.JSONDecodeError:
        return {"type": "error", "error": "bad_json"}

async def send(player, data):
    try:
        player["writer"].write(dumps(data))
        await player["writer"].drain()
    except Exception:
        pass

# ---- Game session on server ----
class Session:
    def __init__(self, pX, pO):
        self.game = Game.new()
        self.players = {"X": pX, "O": pO}
        self.closed = False

    async def broadcast_state(self, terminal_reason: str | None = None):
        msg = {
            "type": "state",
            "board": self.game.board,
            "turn": self.game.turn,
            "terminal": self.game.terminal(),
            "winner": self.game.winner(),
        }
        for p in self.players.values():
            await send(p, msg)
        if terminal_reason or self.game.terminal():
            for p in self.players.values():
                await send(p, {"type": "end", "reason": terminal_reason or ("winner" if self.game.winner() else "draw")})

    async def start(self):
        await send(self.players["X"], {"status":"matched","you":"X","opponent": self.players["O"]["name"]})
        await send(self.players["O"], {"status":"matched","you":"O","opponent": self.players["X"]["name"]})
        await self.broadcast_state()
        await send(self.players["X"], {"type":"your_turn"})
        asyncio.create_task(self.listen_player("X"))
        asyncio.create_task(self.listen_player("O"))

    async def listen_player(self, mark: str):
        reader = self.players[mark]["reader"]
        peer = self.players["O" if mark=="X" else "X"]
        try:
            while not reader.at_eof() and not self.closed:
                msg = await read_json_line(reader)
                if msg is None:
                    break
                mtype = msg.get("type")
                if mtype == "move":
                    idx = int(msg.get("idx", 0))
                    if self.game.turn != mark:
                        await send(self.players[mark], {"type":"error","error":"not_your_turn"})
                        continue
                    if not (1 <= idx <= 9) or not self.game.play(idx):
                        await send(self.players[mark], {"type":"error","error":"invalid_move"})
                        continue
                    await self.broadcast_state()
                    if self.game.terminal():
                        self.closed = True
                        break
                    await send(self.players[self.game.turn], {"type":"your_turn"})
                elif mtype == "quit":
                    self.closed = True
                    await send(peer, {"type":"end","reason":"opponent_quit"})
                    break
                else:
                    pass
        except Exception as e:
            if not self.closed:
                self.closed = True
                await send(peer, {"type":"end","reason":"disconnect"})

# ---- Main server that matches players and (optionally) self-joins ----
class TicTacToeServer:
    def __init__(self, pin: str):
        self.pin = pin
        self.waiting = None
        self.sessions = set()

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        logging.info(f"Conn from {addr}")
        try:
            hello = await asyncio.wait_for(read_json_line(reader), timeout=10.0)
        except asyncio.TimeoutError:
            writer.close(); await writer.wait_closed(); return
        if not hello or hello.get("pin") != self.pin:
            writer.write(dumps({"error":"auth_failed"})); await writer.drain()
            writer.close(); await writer.wait_closed(); return
        name = hello.get("name") or "Player"

        me = {"name": name, "reader": reader, "writer": writer}
        if self.waiting is None:
            self.waiting = me
            writer.write(dumps({"status":"waiting_for_opponent"})); await writer.drain()
            logging.info(f"{name} waiting for opponent")
        else:
            opp = self.waiting
            self.waiting = None
            ses = Session(pX=opp, pO=me)  # first is X, second O
            self.sessions.add(ses)
            await ses.start()

async def self_join(host: str, port: int, pin: str, name: str):
    """Dial the server we just started and take a seat as a normal client."""
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(dumps({"type":"hello","name": name, "pin": pin}))
        await writer.drain()
        # Keep the connection alive; just read and discard to avoid closing.
        while True:
            line = await reader.readline()
            if not line:
                break
        writer.close(); await writer.wait_closed()
    except Exception as e:
        logging.error(f"Self-join failed: {e}")

# ---- Entrypoint ----
async def amain(host, port, pin, discovery_port, host_plays: bool, host_name: str):
    server = TicTacToeServer(pin)
    try:
        srv = await asyncio.start_server(server.handle, host, port)
    except Exception:
        logging.exception("Failed to start TCP server")
        return
    addrs = ", ".join(str(s.getsockname()) for s in srv.sockets)
    logging.info(f"Listening on {addrs} (PIN required)")

    # UDP discovery
    start_udp_discovery_responder(host, discovery_port, host_name, port, True)

    # If host should be a player, auto-dial loopback to take first seat
    if host_plays:
        logging.info("Host-plays enabled: taking a seat via loopback")
        asyncio.create_task(self_join("127.0.0.1", port, pin, host_name))

    async with srv:
        await srv.serve_forever()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--pin", required=True)
    ap.add_argument("--discovery-port", type=int, default=9998)
    ap.add_argument("--host-plays", action="store_true",
                    help="Server auto-joins itself as a player over loopback")
    ap.add_argument("--host-name", default="HostPlayer",
                    help="Display name for host's player when host-plays is on")
    args = ap.parse_args()
    try:
        asyncio.run(amain(args.host, args.port, args.pin, args.discovery_port, args.host_plays, args.host_name))
    except KeyboardInterrupt:
        logging.info("Server stopped")

if __name__ == "__main__":
    main()
