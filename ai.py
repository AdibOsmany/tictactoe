from __future__ import annotations
from typing import Tuple, Optional
from .game import Game, Player

# Minimax with alpha-beta pruning. Returns (best_index, score)

def best_move(game: Game, as_player: Player, depth_limit: Optional[int] = None) -> Tuple[int, int]:
    assert as_player in ("X", "O")

    def minimax(g: Game, alpha: int, beta: int, depth: int) -> Tuple[Optional[int], int]:
        if g.terminal() or (depth_limit is not None and depth >= depth_limit):
            return None, g.score(as_player)
        if g.turn == as_player:
            # Maximizing
            best_idx = None
            best_val = -10
            for i in g.moves():
                idx=i+1
                ng = g.clone(); ng.play(idx)
                _, val = minimax(ng, alpha, beta, depth + 1)
                if val > best_val:
                    best_val, best_idx = val, idx
                alpha = max(alpha, val)
                if beta <= alpha:
                    break
            return best_idx, best_val
        else:
            # Minimizing
            best_idx = None
            best_val = 10
            for i in g.moves():
                idx=i+1
                ng = g.clone(); ng.play(idx)
                _, val = minimax(ng, alpha, beta, depth + 1)
                if val < best_val:
                    best_val, best_idx = val, idx
                beta = min(beta, val)
                if beta <= alpha:
                    break
            return best_idx, best_val

    idx, val = minimax(game, -10, 10, 0)
    # If depth-limited search can't decide, pick first legal move
    if idx is None:
        legal = game.moves()
        idx = legal[0] if legal else -1
        idx+=1
    return idx, val
