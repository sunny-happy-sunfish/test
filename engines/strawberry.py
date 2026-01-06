#!/usr/bin/env python3
import chess
import chess.polyglot
import sys
import time

INF = 100000
INFO_INTERVAL = 0.5

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0
}

PAWN_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10,-20,-20, 10, 10,  5,
     5, -5,-10,  0,  0,-10, -5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5,  5, 10, 25, 25, 10,  5,  5,
    10, 10, 20, 30, 30, 20, 10, 10,
    50, 50, 50, 50, 50, 50, 50, 50,
     0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_PST = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

ROOK_PST = [
     0,  0,  0,  5,  5,  0,  0,  0,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     5, 10, 10, 10, 10, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

QUEEN_PST = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]

KING_PST = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]

KING_ENDGAME_PST = [
     0,  5, 10, 15, 15, 10,  5,  0,
     5, 10, 15, 20, 20, 15, 10,  5,
    10, 15, 20, 25, 25, 20, 15, 10,
    15, 20, 25, 30, 30, 25, 20, 15,
    15, 20, 25, 30, 30, 25, 20, 15,
    10, 15, 20, 25, 25, 20, 15, 10,
     5, 10, 15, 20, 20, 15, 10,  5,
     0,  5, 10, 15, 15, 10,  5,  0
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
nodes = 0
last_info = 0
start_time = 0
time_limit = None

def evaluate(board):
    if board.is_checkmate():
        return -INF
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_threefold_repetition():
        return 0

    score = 0
    pieces = board.piece_map()
    endgame = len(pieces) <= 6

    pawns = {chess.WHITE: [], chess.BLACK: []}

    for sq, piece in pieces.items():
        value = PIECE_VALUES[piece.piece_type]
        idx = sq if piece.color == chess.WHITE else 63 - sq

        if piece.piece_type == chess.KING and endgame:
            pst = KING_ENDGAME_PST[idx]
        else:
            pst = PST[piece.piece_type][idx]

        score += (value + pst) if piece.color == chess.WHITE else -(value + pst)

        if piece.piece_type == chess.PAWN:
            pawns[piece.color].append(sq)

    # pawn structure
    for color, ps in pawns.items():
        files = [p % 8 for p in ps]
        for f in set(files):
            count = files.count(f)
            if count > 1:
                score += (-15 * count) if color == chess.WHITE else (15 * count)

    return score if board.turn else -score

def mvv_lva(board, move):
    if not board.is_capture(move):
        return 0
    victim = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if victim and attacker:
        return 10 * PIECE_VALUES[victim.piece_type] - PIECE_VALUES[attacker.piece_type]
    return 0

def quiescence(board, alpha, beta):
    stand = evaluate(board)
    if stand >= beta:
        return beta
    if stand > alpha:
        alpha = stand

    for move in board.legal_moves:
        if board.is_capture(move):
            board.push(move)
            score = -quiescence(board, -beta, -alpha)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
    return alpha

def negamax(board, depth, alpha, beta):
    global nodes, last_info

    nodes += 1

    if time_limit and time.time() - start_time > time_limit:
        raise TimeoutError

    key = (chess.polyglot.zobrist_hash(board), depth)
    if key in TT:
        return TT[key]

    if depth == 0 or board.is_game_over():
        return quiescence(board, alpha, beta), None

    best_move = None
    moves = list(board.legal_moves)
    moves.sort(key=lambda m: mvv_lva(board, m), reverse=True)

    for move in moves:
        board.push(move)
        score, _ = negamax(board, depth - 1, -beta, -alpha)
        score = -score
        board.pop()

        if score > alpha:
            alpha = score
            best_move = move

            if time.time() - last_info > INFO_INTERVAL:
                elapsed = time.time() - start_time
                nps = int(nodes / elapsed) if elapsed > 0 else 0
                print(f"info depth {depth} score cp {alpha} nodes {nodes} nps {nps} pv {move.uci()}")
                sys.stdout.flush()
                last_info = time.time()

            if alpha >= beta:
                break

    TT[key] = (alpha, best_move)
    return alpha, best_move

def uci_loop():
    global board, TT, nodes, start_time, time_limit

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name StrawberryChess v2.0")
            print("id author MK")
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
                fen = " ".join(parts[1:7])
                board = chess.Board(fen)
                idx = 7
            if idx < len(parts) and parts[idx] == "moves":
                for m in parts[idx + 1:]:
                    board.push(chess.Move.from_uci(m))

        elif line.startswith("go"):
            depth = 5
            movetime = None

            if "depth" in line:
                depth = int(line.split("depth")[1].split()[0])
            if "movetime" in line:
                movetime = int(line.split("movetime")[1].split()[0]) / 1000

            time_limit = movetime
            nodes = 0
            TT.clear()
            start_time = time.time()

            try:
                score, move = negamax(board, depth, -INF, INF)
            except TimeoutError:
                score, move = 0, None

            if move:
                print(f"bestmove {move.uci()}")
            else:
                print("bestmove 0000")
            sys.stdout.flush()

        elif line == "quit":
            break

if __name__ == "__main__":
    uci_loop()
