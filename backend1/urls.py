"""
URL configuration for backend1 project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("authapp.urls")),
    path("api/", include("profiles.urls")),
]

