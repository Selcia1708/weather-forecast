# ══════════════════════════════════════════════════════════════════════════
# apps/users/admin.py
# ══════════════════════════════════════════════════════════════════════════
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserPreferences


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['email', 'username', 'is_staff', 'date_joined']
    search_fields = ['email', 'username']
    ordering      = ['-date_joined']


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display  = ['user', 'units', 'language', 'push_alerts', 'location_consent']
    search_fields = ['user__email']
    list_filter   = ['units', 'language', 'push_alerts']