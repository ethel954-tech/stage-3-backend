from django.urls import path
from . import views

urlpatterns = [
    path('github', views.github_login, name='github-login'),
    path('github/', views.github_login, name='github-login-slash'),
    path('github/callback', views.github_callback, name='github-callback'),
    path('github/callback/', views.github_callback, name='github-callback-slash'),
    path('cli/exchange', views.cli_exchange, name='cli-exchange'),
    path('cli/exchange/', views.cli_exchange, name='cli-exchange-slash'),
    path('refresh', views.refresh_token, name='refresh-token'),
    path('refresh/', views.refresh_token, name='refresh-token-slash'),
    path('logout', views.logout, name='logout'),
    path('logout/', views.logout, name='logout-slash'),
    path('me', views.me, name='me'),
    path('me/', views.me, name='me-slash'),
    path('csrf', views.csrf_token, name='csrf-token'),
    path('csrf/', views.csrf_token, name='csrf-token-slash'),
]

