from django.urls import path
from knox import views as knox_views
from rest_framework.routers import DefaultRouter

#from user.views import ()

api_router = DefaultRouter()
api_router.register(r'users', )

auth_urlpatterns = [
    path('auth/register', '', name='auth-register'),
    path('auth/login', '', name='auth-login'),
    path('auth/logout', knox_views.LogoutView.as_view(), name='auth-logout')
]