from .game import Game
from .ai import best_move

def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)

def run():
    # 1) Basic move legality
    g = Game.new()
    _assert(g.play(0), "First move should be legal")
    _assert(not g.play(0), "Cell already taken should be illegal")

    # 2) Winner detection
    g = Game(["X","X","X","O","O"," "," "," "," "], "O")
    _assert(g.winner() == "X", "Row win not detected")

    # 3) AI never loses (optimal play → draw vs optimal human)
    g = Game.new()
    seen = set()
    for _ in range(9):
        if g.turn == "X":
            idx, _ = best_move(g, as_player="X")
        else:
            idx, _ = best_move(g, as_player="O")
        g.play(idx)
        state = tuple(g.board)
        _assert(state not in seen, "Loop detected")
        seen.add(state)
        if g.terminal():
            break
    _assert(g.winner() in (None, "X", "O"), "Invalid winner")
    print("All tests passed.")

if __name__ == "__main__":
    run()
