from django.contrib import admin
from .models import RefreshToken


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'is_revoked', 'created_at')
    list_filter = ('is_revoked',)

