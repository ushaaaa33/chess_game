from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    """
    Our custom user model.
    
    We inherit from AbstractUser which gives us these fields for FREE:
    - username
    - password (stored as a hash, never plain text)
    - first_name, last_name
    - is_active, is_staff, is_superuser
    - date_joined, last_login
    
    We ADD these extra fields:
    """
    
    # Override email to make it unique (no two accounts with same email)
    email = models.EmailField(unique=True)
    
    # Game statistics
    games_played = models.IntegerField(default=0)
    games_won = models.IntegerField(default=0)
    
    # When was this account created
    created_at = models.DateTimeField(auto_now_add=True)

    # Tell Django to use EMAIL for login instead of username
    USERNAME_FIELD = 'email'
    
    # Fields required when creating a superuser via command line
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        # This controls how a user displays in the admin panel
        return self.email

    @property
    def win_rate(self):
        """Calculate win percentage — usable in templates as user.win_rate"""
        if self.games_played == 0:
            return 0
        return round((self.games_won / self.games_played) * 100, 1)