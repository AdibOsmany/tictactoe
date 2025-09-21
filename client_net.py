import asyncio, argparse, json, sys

ENC = "utf-8"
def dumps(obj): return (json.dumps(obj, separators=(",", ":")) + "\n").encode(ENC)

async def read_json_line(reader: asyncio.StreamReader):
    line = await reader.readline()
    if not line: return None
    try: return json.loads(line.decode(ENC))
    except json.JSONDecodeError: return {"type":"error","error":"bad_json"}

def pretty_board(board):
    def cell(i):
        v = board[i]
        return v if v in ("X","O") else str(i+1)
    r = []
    for row in range(3):
        r.append(f" {cell(row*3)} | {cell(row*3+1)} | {cell(row*3+2)} ")
    return ("\n---+---+---\n").join(r)

async def main(host, port, name, pin):
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(dumps({"type":"hello","name":name,"pin":pin}))
    await writer.drain()
    print(">> Connected. Waiting…")

    async def input_task():
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line: break
            cmd = line.strip().lower()
            if cmd.startswith("move"):
                try:
                    idx = int(cmd.split()[1])
                except Exception:
                    print("!! usage: move <1-9>")
                    continue
                writer.write(dumps({"type":"move","idx":idx}))
                await writer.drain()
            elif cmd in ("quit","exit"):
                writer.write(dumps({"type":"quit"})); await writer.drain()
                break

    async def recv_task():
        while True:
            msg = await read_json_line(reader)
            if msg is None:
                print("<< Disconnected.")
                break
            if msg.get("status") == "waiting_for_opponent":
                print("<< Waiting for opponent…")
            elif msg.get("status") == "matched":
                print(f"<< Matched: you={msg.get('you')} vs {msg.get('opponent')}")
            elif msg.get("type") == "state":
                print(pretty_board(msg["board"]))
                if msg.get("terminal"):
                    print(f"<< Game over — Winner: {msg.get('winner') or 'Draw'}")
            elif msg.get("type") == "your_turn":
                print("<< Your turn. Use: move <1-9>")
            elif msg.get("type") == "end":
                print(f"<< Game ended ({msg.get('reason')}).")
            elif msg.get("type") == "error":
                print("<< ERROR:", msg.get("error"))

    await asyncio.gather(recv_task(), input_task())
    writer.close(); await writer.wait_closed()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--pin", required=True)
    args = ap.parse_args()
    asyncio.run(main(args.host, args.port, args.name, args.pin))
