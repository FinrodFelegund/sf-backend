from django.urls import path
from knox import views as knox_views
from rest_framework.routers import DefaultRouter

from user.views import (
    CSRFTokenView,
    CurrentUserView,
    LoginView,
    RegisterView,
)

api_router = DefaultRouter()
api_router.register(r'registration', RegisterView, basename='registrations')

auth_urlpatterns = [
    path('csrf/', CSRFTokenView.as_view(), name='auth-csrf'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', knox_views.LogoutView.as_view(), name='auth-logout'),
    path('auth/me/',CurrentUserView.as_view(), name='auth-me'),
]