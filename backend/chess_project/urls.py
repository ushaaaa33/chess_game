# from django.contrib import admin
# from django.urls import path, include

# urlpatterns = [
#     path('admin/',    admin.site.urls),
#     path('',          include('accounts.urls')),   # handles / and /login/ etc
#     path('accounts/', include('accounts.urls')),   # handles /accounts/login/ etc
#     path('game/',     include('game.urls')),        # handles /game/
# ]


# from django.contrib import admin
# from django.urls import path, include

# urlpatterns = [
#     path('admin/',    admin.site.urls),
#     path('accounts/', include('accounts.urls')),  # all auth pages
#     path('game/',     include('game.urls')),       # chess game
#     path('',          include('accounts.urls',     # root redirect
#                               namespace='accounts_root')),
# ]


from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/',    admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),  # ← ADD THIS (Google OAuth routes)
    path('game/',     include('game.urls')),
    path('',          lambda request: redirect('accounts:login')),
]