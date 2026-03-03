import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token

from .models import GameSession
from .chess_logic import (
    init_board, get_legal_moves, apply_move,
    ai_move, is_checkmate, is_stalemate, is_in_check
)


# ── Helper: get user from token ──────────
def get_user_from_token(request):
    """
    Reads Authorization: Token xxx header
    Returns user or None
    """
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Token '):
        token_key = auth.split(' ')[1]
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None
    return None


# ════════════════════════════════════════
# 1. MAIN GAME PAGE (browser only)
# ════════════════════════════════════════
@login_required
def index(request):
    game = GameSession.objects.filter(
        player=request.user,
        status='active'
    ).order_by('-updated_at').first()

    if not game:
        game = GameSession(player=request.user)
        game.set_board(init_board())
        game.save()

    return render(request, 'game/index.html', {
        'game': game,
        'user': request.user,
    })


# ════════════════════════════════════════
# 2. NEW GAME (browser only)
# ════════════════════════════════════════
@login_required
def new_game(request):
    GameSession.objects.filter(
        player=request.user,
        status='active'
    ).update(status='draw')

    game = GameSession(player=request.user)
    game.set_board(init_board())
    game.save()
    return redirect('game:index')


# ════════════════════════════════════════
# 3. GAME STATE API (Flutter)
# ════════════════════════════════════════
@csrf_exempt
def game_state(request, game_id):
    # Get user from token
    user = get_user_from_token(request)
    if not user:
        return JsonResponse(
            {'error': 'Not authenticated'},
            status=401
        )

    game = GameSession.objects.filter(
        player=user,
        status='active'
    ).order_by('-updated_at').first()

    if not game:
        game = GameSession(player=user)
        game.set_board(init_board())
        game.save()

    return JsonResponse({
        'game_id': game.id,
        'board':   game.get_board(),
        'turn':    game.turn,
        'status':  game.status,
    })


# ════════════════════════════════════════
# 4. GET VALID MOVES API (Flutter)
# ════════════════════════════════════════
@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def get_moves(request, game_id):
    if request.method == 'OPTIONS':
        return JsonResponse({}, status=200)

    user = get_user_from_token(request)
    if not user:
        return JsonResponse(
            {'error': 'Not authenticated'},
            status=401
        )

    game = get_object_or_404(
        GameSession, id=game_id, player=user
    )

    if game.status != 'active':
        return JsonResponse({'moves': []})

    data  = json.loads(request.body)
    row   = data.get('row')
    col   = data.get('col')
    board = game.get_board()
    piece = board[row][col]

    if not piece or piece['color'] != 'white':
        return JsonResponse({'moves': []})

    legal = get_legal_moves(board, piece, row, col)
    return JsonResponse({'moves': legal})


# ════════════════════════════════════════
# 5. MAKE A MOVE API (Flutter)
# ════════════════════════════════════════
@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def make_move(request, game_id):
    if request.method == 'OPTIONS':
        return JsonResponse({}, status=200)

    user = get_user_from_token(request)
    if not user:
        return JsonResponse(
            {'error': 'Not authenticated'},
            status=401
        )

    game = get_object_or_404(
        GameSession, id=game_id, player=user
    )

    if game.status != 'active':
        return JsonResponse(
            {'error': 'Game is already over'},
            status=400
        )

    data     = json.loads(request.body)
    from_row = data.get('from_row')
    from_col = data.get('from_col')
    to_row   = data.get('to_row')
    to_col   = data.get('to_col')

    board = game.get_board()
    piece = board[from_row][from_col]

    if not piece or piece['color'] != 'white':
        return JsonResponse(
            {'error': 'Not your piece'},
            status=400
        )

    legal = get_legal_moves(board, piece, from_row, from_col)
    if (to_row, to_col) not in legal:
        return JsonResponse(
            {'error': 'Illegal move'},
            status=400
        )

    # Apply player move
    board = apply_move(board, from_row, from_col, to_row, to_col)

    # Check black checkmate
    if is_checkmate(board, 'black'):
        game.set_board(board)
        game.status = 'white_won'
        game.save()
        user.games_played += 1
        user.games_won    += 1
        user.save()
        return JsonResponse({
            'board':   board,
            'status':  'white_won',
            'ai_move': None,
            'message': 'Checkmate! You won! 🏆'
        })

    # Check black stalemate
    if is_stalemate(board, 'black'):
        game.set_board(board)
        game.status = 'draw'
        game.save()
        return JsonResponse({
            'board':   board,
            'status':  'draw',
            'ai_move': None,
            'message': "Draw! 🤝"
        })

    # AI move
    ai_result    = ai_move(board)
    ai_move_data = None

    if ai_result:
        ar, ac, br, bc = ai_result
        ai_move_data   = {'from': [ar, ac], 'to': [br, bc]}
        board          = apply_move(board, ar, ac, br, bc)

        if is_checkmate(board, 'white'):
            game.set_board(board)
            game.status = 'black_won'
            game.save()
            return JsonResponse({
                'board':   board,
                'status':  'black_won',
                'ai_move': ai_move_data,
                'message': 'Checkmate! You lost! 😔'
            })

        if is_stalemate(board, 'white'):
            game.set_board(board)
            game.status = 'draw'
            game.save()
            return JsonResponse({
                'board':   board,
                'status':  'draw',
                'ai_move': ai_move_data,
                'message': "Draw! 🤝"
            })

    game.set_board(board)
    game.save()

    in_check = is_in_check(board, 'white')

    return JsonResponse({
        'board':    board,
        'status':   'active',
        'ai_move':  ai_move_data,
        'in_check': in_check,
        'message':  '⚠️ Check!' if in_check else 'Your turn'
    })