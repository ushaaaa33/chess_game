import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import GameSession
from .chess_logic import (
    init_board, get_legal_moves, apply_move,
    ai_move, is_checkmate, is_stalemate, is_in_check
)


# ─────────────────────────────────────────
# MAIN GAME PAGE
# ─────────────────────────────────────────

@login_required
def index(request):
    """
    Show the chess game page.
    Loads existing active game or creates a new one.
    """
    # Find an active game for this user
    game = GameSession.objects.filter(
        player=request.user,
        status='active'
    ).order_by('-updated_at').first()

    # No active game → create one
    if not game:
        game = GameSession(player=request.user)
        game.set_board(init_board())
        game.save()

    return render(request, 'game/index.html', {
        'game': game,
        'user': request.user,
    })


# ─────────────────────────────────────────
# NEW GAME
# ─────────────────────────────────────────

@login_required
def new_game(request):
    """Abandon current game and start fresh."""
    # Mark any active game as a draw
    GameSession.objects.filter(
        player=request.user,
        status='active'
    ).update(status='draw')

    # Create fresh game
    game = GameSession(player=request.user)
    game.set_board(init_board())
    game.save()

    return redirect('game:index')


# ─────────────────────────────────────────
# GET VALID MOVES (API)
# ─────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def get_moves(request, game_id):
    """
    API endpoint: given a square, return legal moves for the piece there.

    Request:  POST { "row": 6, "col": 4 }
    Response: { "moves": [[5,4], [4,4]] }
    """
    game = get_object_or_404(GameSession, id=game_id, player=request.user)

    if game.status != 'active':
        return JsonResponse({'moves': []})

    data = json.loads(request.body)
    row  = data.get('row')
    col  = data.get('col')

    board = game.get_board()
    piece = board[row][col]

    # Only return moves for white pieces (player's pieces)
    if not piece or piece['color'] != 'white':
        return JsonResponse({'moves': []})

    legal = get_legal_moves(board, piece, row, col)
    return JsonResponse({'moves': legal})


# ─────────────────────────────────────────
# MAKE A MOVE (API)
# ─────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def make_move(request, game_id):
    """
    API endpoint: player makes a move, then AI responds.

    Request:  POST { "from_row":6, "from_col":4, "to_row":4, "to_col":4 }
    Response: { "board": [...], "status": "active", "ai_move": {...} }
    """
    game = get_object_or_404(GameSession, id=game_id, player=request.user)

    if game.status != 'active':
        return JsonResponse({'error': 'Game is already over'}, status=400)

    data     = json.loads(request.body)
    from_row = data.get('from_row')
    from_col = data.get('from_col')
    to_row   = data.get('to_row')
    to_col   = data.get('to_col')

    board = game.get_board()
    piece = board[from_row][from_col]

    # Validate it's a white piece
    if not piece or piece['color'] != 'white':
        return JsonResponse({'error': 'Not your piece'}, status=400)

    # Validate the move is legal
    legal = get_legal_moves(board, piece, from_row, from_col)
    if (to_row, to_col) not in legal:
        return JsonResponse({'error': 'Illegal move'}, status=400)

    # ── Apply player's move ─────────────────
    board = apply_move(board, from_row, from_col, to_row, to_col)

    # ── Check if black is in checkmate ──────
    if is_checkmate(board, 'black'):
        game.set_board(board)
        game.status = 'white_won'
        game.save()
        # Update player stats
        request.user.games_played += 1
        request.user.games_won    += 1
        request.user.save()
        return JsonResponse({
            'board':   board,
            'status':  'white_won',
            'ai_move': None,
            'message': 'Checkmate! You won! 🏆'
        })

    # ── Check if black is in stalemate ──────
    if is_stalemate(board, 'black'):
        game.set_board(board)
        game.status = 'draw'
        game.save()
        request.user.games_played += 1
        request.user.save()
        return JsonResponse({
            'board':   board,
            'status':  'draw',
            'ai_move': None,
            'message': 'Stalemate! It\'s a draw! 🤝'
        })

    # ── AI makes its move ───────────────────
    ai_result   = ai_move(board)
    ai_move_data = None

    if ai_result:
        ar, ac, br, bc = ai_result
        ai_move_data = {
            'from': [ar, ac],
            'to':   [br, bc]
        }
        board = apply_move(board, ar, ac, br, bc)

        # ── Check if white is in checkmate after AI move ──
        if is_checkmate(board, 'white'):
            game.set_board(board)
            game.status = 'black_won'
            game.save()
            request.user.games_played += 1
            request.user.save()
            return JsonResponse({
                'board':   board,
                'status':  'black_won',
                'ai_move': ai_move_data,
                'message': 'Checkmate! You lost! 😔'
            })

        # ── Check stalemate after AI move ────
        if is_stalemate(board, 'white'):
            game.set_board(board)
            game.status = 'draw'
            game.save()
            request.user.games_played += 1
            request.user.save()
            return JsonResponse({
                'board':   board,
                'status':  'draw',
                'ai_move': ai_move_data,
                'message': 'Stalemate! It\'s a draw! 🤝'
            })

    # ── Game continues ──────────────────────
    game.set_board(board)
    game.save()

    # Is white now in check?
    in_check = is_in_check(board, 'white')

    return JsonResponse({
        'board':    board,
        'status':   'active',
        'ai_move':  ai_move_data,
        'in_check': in_check,
        'message':  'Check! Be careful! ⚠️' if in_check else 'Your turn'
    })