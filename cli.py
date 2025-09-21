import argparse
from .game import Game
from .ai import best_move

def parse_args():
    p = argparse.ArgumentParser(description="TicTacToe CLI")
    p.add_argument("--mode", choices=["ai", "human"], default="ai", help="opponent type")
    p.add_argument("--p1", choices=["X", "O"], default="X", help="player 1 mark")
    p.add_argument("--p2", choices=["X", "O"], default="O", help="player 2 mark")
    p.add_argument("--ai-depth", type=int, default=None, help="optional depth limit for AI")
    return p.parse_args()

def read_human_move(g: Game) -> int:
    while True:
        try:
            idx = int(input(f"Play {g.turn} at [1-9]: "))
        except ValueError:
            print("Please type a number 1..9.")
            continue
        if g.play(idx):
            return idx
        print("Illegal move. Try again.")

def run_cli():
    args = parse_args()
    g = Game.new()
    human_vs_human = (args.mode == "human")
    ai_mark = "O" if args.p1 == "X" else "X"  # AI is the other player when in AI mode

    print("Index map:\n1|2|3\n4|5|6\n7|8|9\n")

    while not g.terminal():
        print(g.pretty())
        if human_vs_human or g.turn == args.p1:
            read_human_move(g)
        else:
            idx, _ = best_move(g, as_player=ai_mark, depth_limit=args.ai_depth)
            g.play(idx)
            print(f"AI plays at {idx}")

    print(g.pretty())
    w = g.winner()
    print("Winner:", w if w else "Draw")

if __name__ == "__main__":
    run_cli()
