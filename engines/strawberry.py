#!/usr/bin/env python3
import chess
import chess.polyglot
import sys
import time

INF = 100000
TIME_MARGIN = 0.03
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0
}

PAWN_PST = [
     0, 0, 0, 0, 0, 0, 0, 0,
     5,10,10,-20,-20,10,10,5,
     5,-5,-10,0,0,-10,-5,5,
     0,0,0,20,20,0,0,0,
     5,5,10,25,25,10,5,5,
    10,10,20,30,30,20,10,10,
    50,50,50,50,50,50,50,50,
     0,0,0,0,0,0,0,0
]

KNIGHT_PST = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,0,0,0,0,-20,-40,
    -30,0,10,15,15,10,0,-30,
    -30,5,15,20,20,15,5,-30,
    -30,0,15,20,20,15,0,-30,
    -30,5,10,15,15,10,5,-30,
    -40,-20,0,5,5,0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,0,0,0,0,0,0,-10,
    -10,0,5,10,10,5,0,-10,
    -10,5,5,10,10,5,5,-10,
    -10,0,10,10,10,10,0,-10,
    -10,10,10,10,10,10,10,-10,
    -10,5,0,0,0,0,5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

ROOK_PST = [
     0,0,0,5,5,0,0,0,
    -5,0,0,0,0,0,0,-5,
    -5,0,0,0,0,0,0,-5,
    -5,0,0,0,0,0,0,-5,
    -5,0,0,0,0,0,0,-5,
    -5,0,0,0,0,0,0,-5,
     5,10,10,10,10,10,10,5,
     0,0,0,0,0,0,0,0
]

QUEEN_PST = [
    -20,-10,-10,-5,-5,-10,-10,-20,
    -10,0,0,0,0,0,0,-10,
    -10,0,5,5,5,5,0,-10,
     -5,0,5,5,5,5,0,-5,
      0,0,5,5,5,5,0,-5,
    -10,5,5,5,5,5,0,-10,
    -10,0,5,0,0,0,0,-10,
    -20,-10,-10,-5,-5,-10,-10,-20
]

KING_PST = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20,20,0,0,0,0,20,20,
     20,30,10,0,0,10,30,20
]

KING_ENDGAME_PST = [
     0,5,10,15,15,10,5,0,
     5,10,15,20,20,15,10,5,
    10,15,20,25,25,20,15,10,
    15,20,25,30,30,25,20,15,
    15,20,25,30,30,25,20,15,
    10,15,20,25,25,20,15,10,
     5,10,15,20,20,15,10,5,
     0,5,10,15,15,10,5,0
]

PST = {
    chess.PAWN: PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK: ROOK_PST,
    chess.QUEEN: QUEEN_PST,
    chess.KING: KING_PST
}

board = chess.Board()
TT = {}
start_time = 0
time_limit = None


def material_score(board):
    score = 0
    for p in board.piece_map().values():
        score += PIECE_VALUES[p.piece_type] if p.color else -PIECE_VALUES[p.piece_type]
    return score

def evaluate(board):
    if board.is_checkmate():
        return -INF + 1

    base_material = material_score(board)

    if board.is_stalemate() or board.can_claim_threefold_repetition():
        if abs(base_material) > 300:
            return -200 if board.turn else 200
        return 0

    score = 0
    pieces = board.piece_map()
    endgame = len(pieces) <= 6

    for sq, piece in pieces.items():
        idx = sq if piece.color else 63 - sq
        pst = KING_ENDGAME_PST[idx] if piece.piece_type == chess.KING and endgame else PST[piece.piece_type][idx]
        val = PIECE_VALUES[piece.piece_type] + pst
        score += val if piece.color else -val

    # Hanging pieces penalty
    for sq, piece in pieces.items():
        attackers = board.attackers(not piece.color, sq)
        defenders = board.attackers(piece.color, sq)
        if attackers and not defenders:
            penalty = PIECE_VALUES[piece.piece_type] // 2
            score += -penalty if piece.color else penalty

    return score if board.turn else -score


def mvv_lva(board, move):
    if not board.is_capture(move):
        return 0
    v = board.piece_at(move.to_square)
    a = board.piece_at(move.from_square)
    if v and a:
        return 10 * PIECE_VALUES[v.piece_type] - PIECE_VALUES[a.piece_type]
    return 0

def quiescence(board, alpha, beta):
    stand = evaluate(board)
    if stand >= beta:
        return beta
    if stand > alpha:
        alpha = stand

    for move in board.legal_moves:
        if board.is_capture(move) or board.gives_check(move):
            board.push(move)
            score = -quiescence(board, -beta, -alpha)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
    return alpha

def negamax(board, depth, alpha, beta):
    if time.time() - start_time > time_limit - TIME_MARGIN:
        raise TimeoutError

    key = (chess.polyglot.zobrist_hash(board), depth)
    if key in TT:
        return TT[key]

    if depth == 0 or board.is_game_over():
        return quiescence(board, alpha, beta), None

    best_move = None
    moves = sorted(board.legal_moves, key=lambda m: mvv_lva(board, m), reverse=True)

    for move in moves:
        board.push(move)
        score, _ = negamax(board, depth - 1, -beta, -alpha)
        score = -score
        board.pop()

        if score > alpha:
            alpha = score
            best_move = move
            if alpha >= beta:
                break

    TT[key] = (alpha, best_move)
    return alpha, best_move

def fallback_move(board):
    for m in board.legal_moves:
        if board.is_castling(m):
            return m
    return next(iter(board.legal_moves))

def uci_loop():
    global board, start_time, time_limit

    while True:
        line = sys.stdin.readline()
        if not line:
            return
        line = line.strip()

        if line == "uci":
            print("id name PythonSafeEngine")
            print("id author ChatGPT")
            print("uciok")
            sys.stdout.flush()

        elif line == "isready":
            print("readyok")
            sys.stdout.flush()

        elif line.startswith("position"):
            parts = line.split()
            if "startpos" in parts:
                board = chess.Board()
                idx = parts.index("startpos") + 1
            else:
                board = chess.Board(" ".join(parts[1:7]))
                idx = 7
            if idx < len(parts) and parts[idx] == "moves":
                for m in parts[idx+1:]:
                    board.push(chess.Move.from_uci(m))

        elif line.startswith("go"):
            parts = line.split()
            wtime = btime = winc = binc = None
            movetime = None

            for i, p in enumerate(parts):
                if p == "movetime":
                    movetime = int(parts[i+1]) / 1000
                elif p == "wtime":
                    wtime = int(parts[i+1]) / 1000
                elif p == "btime":
                    btime = int(parts[i+1]) / 1000
                elif p == "winc":
                    winc = int(parts[i+1]) / 1000
                elif p == "binc":
                    binc = int(parts[i+1]) / 1000

            if movetime is None:
                remaining = wtime if board.turn else btime
                inc = winc if board.turn else binc
                movetime = max(0.05, min(remaining * 0.03 + (inc or 0) * 0.8, 1.0))

            if movetime < 0.15:
                max_depth = 2
            elif movetime < 0.3:
                max_depth = 3
            elif movetime < 0.6:
                max_depth = 4
            else:
                max_depth = 5

            start_time = time.time()
            time_limit = movetime
            TT.clear()

            best = fallback_move(board)

            for d in range(1, max_depth + 1):
                try:
                    _, move = negamax(board, d, -INF, INF)
                    if move:
                        best = move
                except TimeoutError:
                    break

            print(f"bestmove {best.uci()}")
            sys.stdout.flush()

        elif line == "quit":
            return


if __name__ == "__main__":
    uci_loop()
