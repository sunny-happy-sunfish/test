#!/usr/bin/env python3
import sys
import time
import chess
import math

INF = 10_000

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

MAX_DEPTH = 4


class Engine:
    def __init__(self):
        self.board = chess.Board()
        self.start_time = 0.0
        self.time_limit = 0.1
        self.nodes = 0
        self.history = []

    # ---------------- Evaluation ----------------

    def material_score(self, board):
        score = 0
        for piece in board.piece_map().values():
            v = PIECE_VALUES[piece.piece_type]
            score += v if piece.color == chess.WHITE else -v
        return score

    def evaluate(self, board):
        if board.is_checkmate():
            return -INF + 1

        if board.is_stalemate() or board.can_claim_threefold_repetition():
            mat = self.material_score(board)
            if abs(mat) > 300:
                return -200 if board.turn == chess.WHITE else 200
            return 0

        score = self.material_score(board) * 1.1
        return score if board.turn == chess.WHITE else -score

    # ---------------- Quiescence ----------------

    def quiescence(self, board, alpha, beta):
        self.nodes += 1
        stand = self.evaluate(board)
        if stand >= beta:
            return beta
        if alpha < stand:
            alpha = stand

        for move in board.legal_moves:
            if not board.is_capture(move):
                continue
            board.push(move)
            score = -self.quiescence(board, -beta, -alpha)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    # ---------------- Search ----------------

    def negamax(self, board, depth, alpha, beta):
        if time.time() - self.start_time > self.time_limit:
            return None

        self.nodes += 1

        if depth == 0:
            return self.quiescence(board, alpha, beta)

        best = -INF

        for move in board.legal_moves:
            board.push(move)
            score = self.negamax(board, depth - 1, -beta, -alpha)
            board.pop()

            if score is None:
                return None

            score = -score
            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break

        return best

    def search(self):
        best_move = None
        alpha = -INF
        beta = INF

        for depth in range(1, MAX_DEPTH + 1):
            if time.time() - self.start_time > self.time_limit:
                break

            local_best = None
            local_alpha = -INF

            for move in self.board.legal_moves:
                self.board.push(move)
                score = self.negamax(self.board, depth - 1, -beta, -alpha)
                self.board.pop()

                if score is None:
                    break

                score = -score
                if score > local_alpha:
                    local_alpha = score
                    local_best = move

            if local_best is not None:
                best_move = local_best
                alpha = local_alpha

        return best_move

    # ---------------- UCI ----------------

    def set_position(self, parts):
        if parts[0] == "startpos":
            self.board = chess.Board()
            moves = parts[2:] if len(parts) > 1 and parts[1] == "moves" else []
        else:
            fen = " ".join(parts[:6])
            self.board = chess.Board(fen)
            moves = parts[6:]

        for m in moves:
            self.board.push_uci(m)

    def go(self, args):
        wtime = btime = winc = binc = 0

        for i in range(len(args)):
            if args[i] == "wtime":
                wtime = int(args[i + 1])
            elif args[i] == "btime":
                btime = int(args[i + 1])
            elif args[i] == "winc":
                winc = int(args[i + 1])
            elif args[i] == "binc":
                binc = int(args[i + 1])

        my_time = wtime if self.board.turn == chess.WHITE else btime
        my_inc = winc if self.board.turn == chess.WHITE else binc

        self.time_limit = max(0.05, my_time / 30_000 + my_inc / 1000 * 0.7)

        self.start_time = time.time()
        self.nodes = 0

        move = self.search()
        if move is None:
            move = next(iter(self.board.legal_moves))

        print(f"bestmove {move.uci()}", flush=True)

    def loop(self):
        while True:
            line = sys.stdin.readline()
            if not line:
                return
            line = line.strip()

            if line == "uci":
                print("id name StrawberryChess v2.5")
                print("id author MK")
                print("uciok")

            elif line == "isready":
                print("readyok")

            elif line.startswith("position"):
                self.set_position(line.split()[1:])

            elif line.startswith("go"):
                self.go(line.split()[1:])

            elif line == "quit":
                return


if __name__ == "__main__":
    Engine().loop()
