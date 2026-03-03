import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def api_signup(request):
    if request.method == 'OPTIONS':
        return JsonResponse({}, status=200)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)

    email     = data.get('email', '').strip()
    username  = data.get('username', '').strip()
    password1 = data.get('password1', '')
    password2 = data.get('password2', '')

    if not email or not username or not password1:
        return JsonResponse({
            'success': False,
            'error': 'All fields are required'
        }, status=400)

    if password1 != password2:
        return JsonResponse({
            'success': False,
            'error': 'Passwords do not match'
        }, status=400)

    if len(password1) < 8:
        return JsonResponse({
            'success': False,
            'error': 'Password must be at least 8 characters'
        }, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({
            'success': False,
            'error': 'Email already registered'
        }, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({
            'success': False,
            'error': 'Username already taken'
        }, status=400)

    try:
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        # Create or get token for this user
        # Token is like a permanent session key
        token, _ = Token.objects.get_or_create(user=user)

        return JsonResponse({
            'success':  True,
            'token':    token.key,   # ← send token to Flutter
            'user_id':  user.id,
            'username': user.username,
            'email':    user.email,
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def api_login(request):
    if request.method == 'OPTIONS':
        return JsonResponse({}, status=200)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)

    email    = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return JsonResponse({
            'success': False,
            'error': 'Email and password required'
        }, status=400)

    # Find user by email
    try:
        user_obj = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Invalid email or password'
        }, status=401)

    # Check password
    user = authenticate(
        request,
        username=user_obj.username,
        password=password
    )

    if user is not None:
        # Get or create token
        token, _ = Token.objects.get_or_create(user=user)

        return JsonResponse({
            'success':  True,
            'token':    token.key,   # ← send token to Flutter
            'user_id':  user.id,
            'username': user.username,
            'email':    user.email,
        })

    return JsonResponse({
        'success': False,
        'error': 'Invalid email or password'
    }, status=401)


@csrf_exempt
def api_logout(request):
    # Delete token so it can't be used again
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Token '):
        token_key = auth_header.split(' ')[1]
        try:
            Token.objects.filter(key=token_key).delete()
        except Exception:
            pass
    return JsonResponse({'success': True})


@csrf_exempt
def api_check_auth(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Token '):
        token_key = auth_header.split(' ')[1]
        try:
            token = Token.objects.get(key=token_key)
            return JsonResponse({
                'authenticated': True,
                'user_id':  token.user.id,
                'username': token.user.username,
            })
        except Token.DoesNotExist:
            pass
    return JsonResponse({'authenticated': False}, status=401)