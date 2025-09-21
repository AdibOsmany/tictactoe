from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple

Player = str  # "X" or "O"

@dataclass
class Game:
    board: List[str]
    turn: Player = "X"

    @classmethod
    def new(cls) -> "Game":
        return cls([" "] * 9, "X")

    def clone(self) -> "Game":
        return Game(self.board.copy(), self.turn)

    def moves(self) -> List[int]:
        return [i for i, c in enumerate(self.board) if c == " "]

    def play(self, idx: int) -> bool:
        """Attempt to play at index (1..9). Returns True if success."""
        idx=idx-1
        if 0 <= idx < 9 and self.board[idx] == " " and self.winner() is None:
            self.board[idx] = self.turn
            self.turn = "O" if self.turn == "X" else "X"
            return True
        return False
    

    def winner(self) -> Optional[Player]:
        b = self.board
        lines = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
            (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
            (0, 4, 8), (2, 4, 6)              # diags
        ]
        for a, c, d in lines:
            if b[a] != " " and b[a] == b[c] == b[d]:
                return b[a]
        return None

    def terminal(self) -> bool:
        return self.winner() is not None or all(c != " " for c in self.board)

    def score(self, max_player: Player) -> int:
        w = self.winner()
        if w == max_player:
            return +1
        if w and w != max_player:
            return -1
        return 0  # draw or non-terminal (only used at leaf)

    def pretty(self) -> str:
        b = self.board
        rows = [" | ".join(b[i:i+3]) for i in range(0, 9, 3)]
        return f"\n{rows[0]}\n---------\n{rows[1]}\n---------\n{rows[2]}\n"
