
# ══════════════════════════════════════════════════════════════════════════
# apps/notifications/models.py
# ══════════════════════════════════════════════════════════════════════════
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PushNotificationLog(models.Model):
    """Audit log for every push notification attempt."""
    STATUS_CHOICES = [('sent','Sent'),('failed','Failed'),('skipped','Skipped')]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_logs')
    title      = models.CharField(max_length=200)
    body       = models.TextField()
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    error_msg  = models.TextField(blank=True)
    sent_at    = models.DateTimeField(auto_now_add=True)
    alert_event = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f'{self.user.email} – {self.title} [{self.status}]'