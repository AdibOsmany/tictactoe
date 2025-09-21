# tictactoe/discover.py
from __future__ import annotations
import socket
import json
import time
from typing import List, Dict, Any, Tuple

ENC = "utf-8"
DISCOVERY_MAGIC = b"TTT_DISCOVER_V1"

def discover_lan(timeout: float = 1.5, port: int = 9998, broadcast_addr: str = "<broadcast>") -> List[Dict[str, Any]]:
    """
    Broadcast a discovery ping on UDP `port` and collect TicTacToe server replies.

    Returns: list of dicts like
      {
        "ip": "10.0.0.30",
        "port": 54321,
        "name": "Bob",
        "pin_required": True,
        "service": "tictactoe",
        "proto": 1
      }
    """
    results: List[Dict[str, Any]] = []
    seen: set[Tuple[str, int]] = set()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.25)

        # Bind to an ephemeral port so we can receive replies
        sock.bind(("", 0))

        # Send discovery probe
        try:
            sock.sendto(DISCOVERY_MAGIC, (broadcast_addr, port))
        except OSError:
            # Some networks don’t like <broadcast>; try 255.255.255.255 as a fallback
            try:
                sock.sendto(DISCOVERY_MAGIC, ("255.255.255.255", port))
            except Exception:
                pass

        # Collect replies until timeout window closes
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except Exception:
                break

            ip = addr[0]
            try:
                payload = json.loads(data.decode(ENC))
            except Exception:
                continue

            if not isinstance(payload, dict):
                continue
            if payload.get("service") != "tictactoe":
                continue

            host_port = int(payload.get("port") or 0)
            if host_port <= 0:
                continue

            key = (ip, host_port)
            if key in seen:
                continue
            seen.add(key)

            results.append({
                "ip": ip,
                "port": host_port,
                "name": payload.get("name") or "Host",
                "pin_required": bool(payload.get("pin_required", True)),
                "service": payload.get("service"),
                "proto": payload.get("proto"),
            })

    finally:
        sock.close()

    # Sort by IP then port for consistency
    results.sort(key=lambda r: (r["ip"], r["port"]))
    return results


# Optional CLI for testing: `python -m tictactoe.discover --port 9998`
def _parse_args():
    import argparse
    ap = argparse.ArgumentParser(description="Discover TicTacToe hosts on LAN.")
    ap.add_argument("--port", type=int, default=9998)
    ap.add_argument("--timeout", type=float, default=1.5)
    return ap.parse_args()

def main():
    args = _parse_args()
    hosts = discover_lan(timeout=args.timeout, port=args.port)
    if not hosts:
        print("No hosts found.")
        return
    for h in hosts:
        print(f"{h['ip']}:{h['port']}  {h.get('name','Host')}  (pin_required={h.get('pin_required', True)})")

if __name__ == "__main__":
    main()
