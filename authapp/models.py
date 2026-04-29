import hashlib
import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta

from users.models import User


class RefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_revoked = models.BooleanField(default=False)

    class Meta:
        db_table = 'refresh_tokens'
        ordering = ['-created_at']

    @classmethod
    def generate_token(cls):
        return secrets.token_urlsafe(48)

    @classmethod
    def hash_token(cls, token):
        return hashlib.sha256(token.encode()).hexdigest()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_revoked and not self.is_expired()

    def revoke(self):
        self.is_revoked = True
        self.save(update_fields=['is_revoked'])

