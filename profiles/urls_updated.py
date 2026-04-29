from django.urls import path
from .views import ProfileViewSet

profile_list = ProfileViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

profile_detail = ProfileViewSet.as_view({
    'get': 'retrieve',
    'delete': 'destroy',
})

profile_search = ProfileViewSet.as_view({
    'get': 'search',
})

urlpatterns = [
    path('profiles', profile_list, name='profile-list'),
    path('profiles/', profile_list, name='profile-list-slash'),
    path('profiles/<uuid:pk>', profile_detail, name='profile-detail'),
    path('profiles/<uuid:pk>/', profile_detail, name='profile-detail-slash'),
    path('profiles/search/', profile_search, name='profile-search'),  # NEW
]

