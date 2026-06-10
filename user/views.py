from django.contrib.auth.models import update_last_login
from knox.models import AuthToken
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from user.models import CustomUser
from user.serializer import (
    AuthTokenSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserDetailedSerializer,
    UserListSerializer,
)

# Create your views here.

class CSRFTokenView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({'detail': 'CSRF Token set successfully'})

class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'

class UserViewSet():
    pass

class RegisterView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        request=RegisterSerializer,
        responses={201: UserDetailedSerializer},
        description='Register a new user and return tbd',
    )
    def post(self, request):
        pass


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        request=LoginSerializer,
        responses={200: AuthTokenSerializer},
        description='Login with username and password, returns authentication token',
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        update_last_login(None, user)

        instance, token = AuthToken.objects.create(user)

        return Response(
            {
                'token': token,
                'expiry': instance.expiry,
                'user': UserDetailedSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
    
    

