# ══════════════════════════════════════════════════════════════════════════
# apps/users/models.py
# ══════════════════════════════════════════════════════════════════════════
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.email


class UserPreferences(models.Model):
    UNIT_CHOICES = [
        ('metric',   _('Metric (°C, m/s)')),
        ('imperial', _('Imperial (°F, mph)')),
        ('standard', _('Standard (K)')),
    ]
    SEVERITY_CHOICES = [
        ('minor',    _('Minor')),
        ('moderate', _('Moderate')),
        ('severe',   _('Severe')),
        ('extreme',  _('Extreme')),
    ]
    LANG_CHOICES = [
        ('en', 'English'), ('hi', 'Hindi'), ('fr', 'Français'),
        ('de', 'Deutsch'), ('es', 'Español'), ('ar', 'العربية'),
        ('zh-hans', '中文'), ('ja', '日本語'),
    ]

    user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    units              = models.CharField(max_length=10, choices=UNIT_CHOICES, default='metric')
    language           = models.CharField(max_length=10, choices=LANG_CHOICES, default='en')
    push_alerts        = models.BooleanField(default=True)
    alert_severity     = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='moderate')
    fcm_token          = models.CharField(max_length=500, blank=True, help_text='Firebase Cloud Messaging token')
    location_consent   = models.BooleanField(default=False, help_text='GDPR: user consented to location storage')
    data_retention_days = models.PositiveIntegerField(default=30)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('User Preferences')

    def __str__(self):
        return f'{self.user.email} – prefs'