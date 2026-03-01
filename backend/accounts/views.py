from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import SignupForm, LoginForm

def home(request):
    if request.user.is_authenticated:
        return redirect('game:index')
    return redirect('accounts:login')

def signup_view(request):
    # If already logged in, no need to sign up again
    if request.user.is_authenticated:
        return redirect('game:index')

    if request.method == 'POST':
        # POST: form was submitted — validate it
        form = SignupForm(request.POST)

        if form.is_valid():
            # save() creates the user AND hashes the password automatically
            user = form.save()

            # Log the user in immediately after signup
            # This creates a session in the database
            login(request, user,
                  backend='django.contrib.auth.backends.ModelBackend')

            messages.success(
                request, f"Welcome to Chess, {user.username}! 🎉"
            )
            return redirect('game:index')
        else:
            # Form has errors — they'll show in the template automatically
            messages.error(request, "Please fix the errors below.")

    else:
        # GET: user just visited the page — show empty form
        form = SignupForm()

    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('game:index')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            # get_user() returns the authenticated user object
            user = form.get_user()

            # login() creates the session + sets the cookie
            login(request, user)

            messages.success(request, f"Welcome back, {user.username}! ♟")

            # If user was redirected here from a protected page,
            # send them back to where they were trying to go
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('game:index')

        else:
            messages.error(request, "Invalid email or password. Try again.")

    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    # logout() deletes the session from the database
    # and removes the cookie from the browser
    logout(request)
    messages.info(request, "You've been logged out. See you next time!")
    return redirect('accounts:login')