from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'github_id', 'email', 'role', 'is_active', 'last_login_at', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email', 'github_id')

