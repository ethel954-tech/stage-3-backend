from django.urls import path
from .views import ProfileViewSet
from authapp.views import me

profile_list = ProfileViewSet.as_view({
    "get": "list",
    "post": "create",
})
profile_detail = ProfileViewSet.as_view({
    "get": "retrieve",
    "delete": "destroy",
})
profile_search = ProfileViewSet.as_view({
    "get": "search",
})
profile_export = ProfileViewSet.as_view({
    "get": "export",
})

urlpatterns = [
    path("profiles", profile_list, name="profile-list"),
    path("profiles/", profile_list, name="profile-list-slash"),
    path("profiles/export", profile_export, name="profile-export"),
    path("profiles/export/", profile_export, name="profile-export-slash"),
    path("profiles/<uuid:pk>", profile_detail, name="profile-detail"),
    path("profiles/<uuid:pk>/", profile_detail, name="profile-detail-slash"),
    path("profiles/search/", profile_search, name="profile-search"),
    # User management endpoint - /api/users/me
    path("users/me", me, name="users-me"),
    path("users/me/", me, name="users-me-slash"),
]

