from django.db import models
from uuid6 import uuid7


class User(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_ANALYST = 'analyst'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_ANALYST, 'Analyst'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    github_id = models.CharField(max_length=50, unique=True)
    username = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, blank=True, null=True)
    avatar_url = models.URLField(max_length=500, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_ANALYST)
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'github_id'
    REQUIRED_FIELDS = []

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return f"@{self.username}"

    @property
    def is_staff(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_superuser(self):
        return self.role == self.ROLE_ADMIN

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff

