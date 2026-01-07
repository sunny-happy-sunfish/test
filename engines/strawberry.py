#!/usr/bin/env python3
import chess
import chess.engine
import sys

INF = 10000
DEPTH = 5

class BoardWithReps(chess.Board):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rep_counts = {}

    def push(self, move):
        super().push(move)
        fen = self.fen()
        self.rep_counts[fen] = self.rep_counts.get(fen, 0) + 1

    def pop(self):
        fen = self.fen()
        super().pop()
        self.rep_counts[fen] = self.rep_counts.get(fen, 1) - 1


def evaluate(board):
    if board.is_checkmate():
        return -INF if board.turn else INF
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    eval_score = 0
    piece_values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
                    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000}
    for piece_type in piece_values:
        eval_score += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
        eval_score -= len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]
    return eval_score


def negamax(board, depth, alpha, beta):
    fen = board.fen()
    if board.rep_counts.get(fen, 0) >= 3:
        return 0, None  # троекратное повторение

    if depth == 0 or board.is_game_over():
        return evaluate(board), None

    max_eval = -INF
    best_move = None

    for move in board.legal_moves:
        board.push(move)
        eval_score, _ = negamax(board, depth-1, -beta, -alpha)
        eval_score = -eval_score
        board.pop()

        if eval_score > max_eval:
            max_eval = eval_score
            best_move = move
        alpha = max(alpha, eval_score)
        if alpha >= beta:
            break

    return max_eval, best_move


def uci_loop():
    board = BoardWithReps()
    print("id name StrawberryChess v3.0")
    print("id author MK")
    print("uciok")

    while True:
        line = sys.stdin.readline().strip()
        if line == "isready":
            print("readyok")
        elif line.startswith("position"):
            tokens = line.split()
            if "startpos" in tokens:
                board.reset()
            if "moves" in tokens:
                moves_index = tokens.index("moves") + 1
                for move_str in tokens[moves_index:]:
                    board.push_uci(move_str)
        elif line.startswith("go"):
            _, move = negamax(board, DEPTH, -INF, INF)
            if move:
                print(f"bestmove {move.uci()}")
        elif line == "quit":
            break


if __name__ == "__main__":
    uci_loop()
