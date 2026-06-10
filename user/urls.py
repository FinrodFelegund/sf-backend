from django.urls import path
from knox import views as knox_views
from rest_framework.routers import DefaultRouter

from user.views import (
    LoginView,
    RegisterView,
    UserViewSet,
    CSRFTokenView,
)

api_router = DefaultRouter()
#api_router.register(r'users', UserViewSet)

auth_urlpatterns = [
    path('csrf/', CSRFTokenView.as_view(), name='auth-csrf'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', knox_views.LogoutView.as_view(), name='auth-logout')
]