"""
chess_logic.py
==============
Pure Python chess logic — no Pygame, no graphics.
The board is a list of lists where each cell is either:
  - None (empty square)
  - A dict like: {'color': 'white', 'type': 'pawn', 'has_moved': False}
"""

import random
import copy


# ─────────────────────────────────────────
# BOARD INITIALIZATION
# ─────────────────────────────────────────

def create_piece(color, ptype):
    """Create a piece dictionary."""
    return {
        'color': color,   # 'white' or 'black'
        'type': ptype,    # 'pawn','rook','knight','bishop','queen','king'
        'has_moved': False
    }


def init_board():
    """
    Create the starting chess board.
    Returns an 8x8 list of lists.
    Row 0 = black's back rank, Row 7 = white's back rank.
    """
    # Start with all empty squares
    board = [[None for _ in range(8)] for _ in range(8)]

    # ── Pawns ──────────────────────────────
    for col in range(8):
        board[1][col] = create_piece('black', 'pawn')
        board[6][col] = create_piece('white', 'pawn')

    # ── Rooks ──────────────────────────────
    board[0][0] = create_piece('black', 'rook')
    board[0][7] = create_piece('black', 'rook')
    board[7][0] = create_piece('white', 'rook')
    board[7][7] = create_piece('white', 'rook')

    # ── Knights ────────────────────────────
    board[0][1] = create_piece('black', 'knight')
    board[0][6] = create_piece('black', 'knight')
    board[7][1] = create_piece('white', 'knight')
    board[7][6] = create_piece('white', 'knight')

    # ── Bishops ────────────────────────────
    board[0][2] = create_piece('black', 'bishop')
    board[0][5] = create_piece('black', 'bishop')
    board[7][2] = create_piece('white', 'bishop')
    board[7][5] = create_piece('white', 'bishop')

    # ── Queens ─────────────────────────────
    board[0][3] = create_piece('black', 'queen')
    board[7][3] = create_piece('white', 'queen')

    # ── Kings ──────────────────────────────
    board[0][4] = create_piece('black', 'king')
    board[7][4] = create_piece('white', 'king')

    return board


# ─────────────────────────────────────────
# MOVE GENERATION
# ─────────────────────────────────────────

def get_valid_moves(board, piece, row, col):
    """
    Returns list of (row, col) tuples this piece can move to.
    Does NOT check if move leaves own king in check yet —
    that's handled separately in get_legal_moves().
    """
    moves = []
    color   = piece['color']
    ptype   = piece['type']
    opponent = 'black' if color == 'white' else 'white'

    # Directions for sliding pieces
    sliding_directions = {
        'rook':   [(1,0),(-1,0),(0,1),(0,-1)],
        'bishop': [(1,1),(1,-1),(-1,1),(-1,-1)],
        'queen':  [(1,0),(-1,0),(0,1),(0,-1),
                   (1,1),(1,-1),(-1,1),(-1,-1)],
    }

    # ── PAWN ───────────────────────────────
    if ptype == 'pawn':
        # White moves UP (row decreases), black moves DOWN (row increases)
        direction  = -1 if color == 'white' else 1
        start_row  =  6 if color == 'white' else 1

        # One square forward (only if empty)
        new_row = row + direction
        if 0 <= new_row < 8 and board[new_row][col] is None:
            moves.append((new_row, col))

            # Two squares forward from starting position
            if row == start_row and board[row + 2*direction][col] is None:
                moves.append((row + 2*direction, col))

        # Diagonal captures
        for dc in [-1, 1]:
            nc = col + dc
            if 0 <= new_row < 8 and 0 <= nc < 8:
                target = board[new_row][nc]
                if target and target['color'] == opponent:
                    moves.append((new_row, nc))

    # ── SLIDING PIECES (rook, bishop, queen) ──
    elif ptype in sliding_directions:
        for dr, dc in sliding_directions[ptype]:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                if board[r][c] is None:
                    # Empty square — can move here and keep going
                    moves.append((r, c))
                elif board[r][c]['color'] == opponent:
                    # Enemy piece — can capture but can't go further
                    moves.append((r, c))
                    break
                else:
                    # Own piece — blocked
                    break
                r += dr
                c += dc

    # ── KNIGHT ─────────────────────────────
    elif ptype == 'knight':
        # L-shaped jumps — can leap over other pieces
        jumps = [
            (2,1),(2,-1),(-2,1),(-2,-1),
            (1,2),(1,-2),(-1,2),(-1,-2)
        ]
        for dr, dc in jumps:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = board[r][c]
                if target is None or target['color'] == opponent:
                    moves.append((r, c))

    # ── KING ───────────────────────────────
    elif ptype == 'king':
        # One square in any direction
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < 8 and 0 <= c < 8:
                    target = board[r][c]
                    if target is None or target['color'] == opponent:
                        moves.append((r, c))

    return moves


# ─────────────────────────────────────────
# APPLYING MOVES
# ─────────────────────────────────────────

def apply_move(board, from_row, from_col, to_row, to_col):
    """
    Apply a move and return a NEW board (original unchanged).
    Also handles pawn promotion automatically.
    """
    # Deep copy so we don't modify the original board
    new_board = copy.deepcopy(board)

    piece = new_board[from_row][from_col]

    # Move piece to new square
    new_board[to_row][to_col] = piece
    new_board[from_row][from_col] = None

    # Mark piece as moved (used for castling / two-square pawn rule)
    piece['has_moved'] = True

    # ── Pawn Promotion ──────────────────────
    # If pawn reaches the opposite end → becomes a queen automatically
    if piece['type'] == 'pawn':
        if (piece['color'] == 'white' and to_row == 0) or \
           (piece['color'] == 'black' and to_row == 7):
            piece['type'] = 'queen'

    return new_board


# ─────────────────────────────────────────
# CHECK DETECTION
# ─────────────────────────────────────────

def find_king(board, color):
    """Find the position of the king of given color."""
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p and p['color'] == color and p['type'] == 'king':
                return (r, c)
    return None


def is_in_check(board, color):
    """
    Returns True if the king of `color` is currently under attack.
    We check if any opponent piece can reach the king's square.
    """
    king_pos = find_king(board, color)
    if not king_pos:
        return False

    opponent = 'black' if color == 'white' else 'white'

    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece['color'] == opponent:
                # Can this opponent piece reach our king?
                if king_pos in get_valid_moves(board, piece, r, c):
                    return True
    return False


def get_legal_moves(board, piece, row, col):
    """
    Returns only moves that don't leave own king in check.
    This is the FINAL list of moves a player can actually make.
    """
    legal = []
    candidates = get_valid_moves(board, piece, row, col)

    for move in candidates:
        # Try the move on a test board
        test_board = apply_move(board, row, col, move[0], move[1])
        # Only keep the move if it doesn't leave our king in check
        if not is_in_check(test_board, piece['color']):
            legal.append(move)

    return legal


# ─────────────────────────────────────────
# GAME STATE CHECKS
# ─────────────────────────────────────────

def is_checkmate(board, color):
    """
    Returns True if `color` is in checkmate.
    Checkmate = in check AND no legal moves exist.
    """
    # Must be in check first
    if not is_in_check(board, color):
        return False

    # Check if ANY piece has ANY legal move
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece['color'] == color:
                if get_legal_moves(board, piece, r, c):
                    # Found at least one legal move → not checkmate
                    return False

    # In check + zero legal moves = checkmate
    return True


def is_stalemate(board, color):
    """
    Returns True if `color` is in stalemate.
    Stalemate = NOT in check BUT no legal moves exist (it's a draw).
    """
    if is_in_check(board, color):
        return False

    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece['color'] == color:
                if get_legal_moves(board, piece, r, c):
                    return False
    return True


# ─────────────────────────────────────────
# AI OPPONENT
# ─────────────────────────────────────────

def ai_move(board):
    """
    Simple AI: picks a random legal move for black.
    Returns (from_row, from_col, to_row, to_col) or None.

    In Phase 10 we can upgrade this to a smarter AI.
    """
    all_moves = []

    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece['color'] == 'black':
                legal = get_legal_moves(board, piece, r, c)
                for move in legal:
                    all_moves.append((r, c, move[0], move[1]))

    if all_moves:
        return random.choice(all_moves)

    # No moves available (checkmate or stalemate)
    return None