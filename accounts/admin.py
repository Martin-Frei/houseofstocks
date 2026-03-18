# accounts/admin.py
from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'tier', 'created_at']
    list_filter = ['tier']
    search_fields = ['user__email']
    list_editable = ['tier']  # Stufe direkt in der Liste ändern