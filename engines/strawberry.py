#!usr/bin/env python3
import chess
import chess.engine

INF = 1_000_000
MAX_DEPTH = 5  # можно увеличить для сильнее игры

# Простые ценности фигур
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

def piece_value(piece):
    if piece is None:
        return 0
    return PIECE_VALUES.get(piece.piece_type, 0)

def quiescence(board, alpha, beta):
    """
    Простейшая квази-поисковая функция для избежания "фигуры на одной клетке".
    """
    stand_pat = evaluate(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

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

def evaluate(board):
    """
    Простая оценка позиции по материалу
    """
    eval_score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            value = piece_value(piece)
            eval_score += value if piece.color == chess.WHITE else -value
    return eval_score

def negamax(board, depth, alpha, beta, color=1):
    fen = board.fen()
    if not hasattr(board, 'rep_counts'):
        board.rep_counts = {}
    board.rep_counts[fen] = board.rep_counts.get(fen, 0) + 1

    if board.is_checkmate():
        return -INF + (MAX_DEPTH - depth), None
    if board.is_stalemate() or board.rep_counts[fen] >= 3:
        return 0, None
    if depth == 0:
        return color * quiescence(board, alpha, beta), None

    max_eval = -INF
    best_move = None
    for move in board.legal_moves:
        # Не отдаём фигуру без компенсации
        if board.is_capture(move):
            captured_value = piece_value(board.piece_at(move.to_square))
            moving_value = piece_value(board.piece_at(move.from_square))
            if moving_value > captured_value + 10:  # минимальная потеря 10 очков
                continue

        board.push(move)
        eval_score, _ = negamax(board, depth-1, -beta, -alpha, -color)
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
    board = chess.Board()
    print("id name StrawberryChess v3.0.3")
    print("id author MK")
    print("uciok")

    while True:
        command = input()
        if command == "isready":
            print("readyok")
        elif command.startswith("position"):
            tokens = command.split()
            if "startpos" in tokens:
                board.reset()
            if "moves" in tokens:
                moves_index = tokens.index("moves") + 1
                for move in tokens[moves_index:]:
                    board.push_uci(move)
        elif command.startswith("go"):
            eval_score, move = negamax(board, MAX_DEPTH, -INF, INF)
            if move:
                print(f"info score cp {eval_score}")
                print(f"bestmove {move.uci()}")
        elif command == "quit":
            break

if __name__ == "__main__":
    uci_loop()
