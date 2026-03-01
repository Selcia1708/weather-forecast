# ══════════════════════════════════════════════════════════════════════════
# apps/locations/admin.py
# ══════════════════════════════════════════════════════════════════════════
from django.contrib import admin
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display  = ['city', 'country', 'user', 'latitude', 'longitude', 'is_default', 'created_at']
    search_fields = ['city', 'country', 'user__email']
    list_filter   = ['country', 'is_default']
    ordering      = ['-created_at']