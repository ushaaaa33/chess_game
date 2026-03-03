from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import api_views   # ← ADD THIS

app_name = 'accounts'

urlpatterns = [

    # ── Existing web views ────────────────
    path('',        views.home,        name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── NEW Flutter API endpoints ─────────
    path('api/signup/',    api_views.api_signup,    name='api_signup'),
    path('api/login/',     api_views.api_login,     name='api_login'),
    path('api/logout/',    api_views.api_logout,    name='api_logout'),
    path('api/check/',     api_views.api_check_auth, name='api_check'),

    # ── Password Reset ────────────────────
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            email_template_name='accounts/password_reset_email.txt',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url='/accounts/password-reset/done/'
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'password-reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/accounts/password-reset/complete/'
        ),
        name='password_reset_confirm'
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]