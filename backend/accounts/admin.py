from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Columns shown in the admin user list
    list_display = ('email', 'username', 'games_played', 'games_won', 'is_staff')
    
    # Make these columns clickable for searching
    search_fields = ('email', 'username')
    
    # Add our custom fields to the admin edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Chess Stats', {
            'fields': ('games_played', 'games_won')
        }),
    )