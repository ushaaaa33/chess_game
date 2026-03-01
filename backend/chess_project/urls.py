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