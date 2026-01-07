#!/usr/bin/env python3
import chess
import chess.polyglot
import sys
import time

INF = 100000
TIME_MARGIN = 0.05
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

def negamax(board, depth, alpha, beta, root=True):
    global nodes, start_time
    nodes += 1
    if time_limit and time.time() - start_time > time_limit - TIME_MARGIN:
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
        score, _ = negamax(board, depth - 1, -beta, -alpha, root=False)
        score = -score
        board.pop()
        if score > alpha:
            alpha = score
            best_move = move
            if alpha >= beta:
                break

    TT[key] = (alpha, best_move)
    return alpha, best_move


def pick_reasonable_fallback(board):
    for move in board.legal_moves:
        piece = board.piece_at(move.from_square)
        if board.is_castling(move):
            return move
        if piece and piece.piece_type in (chess.PAWN, chess.KNIGHT):
            return move
    return next(iter(board.legal_moves), None)


def uci_loop():
    global board, TT, nodes, start_time, time_limit
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if line == "uci":
            print("id name StrawberryChess v2.3")
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

            fallback = pick_reasonable_fallback(board)
            best_move = fallback
            best_score = -INF

            if movetime and movetime < 0.2:
                max_depth = 3
            elif movetime and movetime < 0.5:
                max_depth = 4
            else:
                max_depth = depth

            start_time = time.time()
            nodes = 0
            TT.clear()
            time_limit = movetime


            for d in range(1, max_depth + 1):
                try:
                    score, move = negamax(board, d, -INF, INF)
                    if move:
                        best_move = move
                        best_score = score
                except TimeoutError:
                    break
                if time_limit and time.time() - start_time > time_limit - TIME_MARGIN:
                    break


            if best_move:
                print(f"bestmove {best_move.uci()}")
            else:
                print("bestmove 0000")
            sys.stdout.flush()
        elif line == "quit":
            break


if __name__ == "__main__":
    try:
        uci_loop()
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.stderr.flush()
    finally:
        while True:
            time.sleep(1)
