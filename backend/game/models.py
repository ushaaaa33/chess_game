from django.db import models
from django.conf import settings
import json


class GameSession(models.Model):

    STATUS_CHOICES = [
        ('active',    'Active'),
        ('white_won', 'White Won'),
        ('black_won', 'Black Won'),
        ('draw',      'Draw'),
    ]

    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='games'
    )
    board_state = models.TextField(default='')
    turn        = models.CharField(max_length=10, default='white')
    status      = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_board(self):
        """Convert stored JSON string → Python list."""
        if self.board_state:
            return json.loads(self.board_state)
        return None

    def set_board(self, board_data):
        """Convert Python list → JSON string for storage."""
        self.board_state = json.dumps(board_data)

    def __str__(self):
        return f"Game #{self.id} — {self.player.username} ({self.status})"