import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from knox.models import AuthToken
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from shared.email.smtp import send_register_mail
from user.models import RegisterUser
from user.serializer import (
    AuthTokenSerializer,
    LoginSerializer,
    RegisterUserSerializer,
    UnlockUserSerializer,
    UserDetailedSerializer,
)

User = get_user_model()

# Create your views here.

class CSRFTokenView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({'detail': 'CSRF Token set successfully'})

class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'

class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(
            {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
            }
        )

class RegisterView(ModelViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request, *args, **kwargs):
        serializer = RegisterUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        duplicate = User.objects.filter(username=user.username, email=user.email).exists()

        if duplicate:
            return Response(
                {
                    'detail': 'User with this emial or username already exists'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        duplicate = RegisterUser.objects.filter(username=user.username, email=user.email).first()
        if duplicate is not None:
            return Response(
                {
                    'id': duplicate.id,
                    'unlockCode': duplicate.unlockcode,
                },
                status=status.HTTP_200_OK,
            )

        unlockcode = ''.join(map(str, random.sample(range(9), 6)))
        user.unlockcode = unlockcode
        user.save()

        send_register_mail(user.email, unlockcode)

        return Response(
            {
                'id': user.id,
                'unlockCode': unlockcode,
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='unlock')
    def unlock(self, request, *args, **kwargs):
        serializer = UnlockUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id = serializer.validated_data['id']


        register_user = RegisterUser.objects.filter(id=id).first()
        if not register_user:
            return Response(
                {
                    'detail': 'A register with this id does not exist'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        duplicate = User.objects.filter(username=register_user.username, email=register_user.email).exists()
        if duplicate:
            return Response(
                {
                    'detail': 'A user with this user name or email already exists'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User(
            username=register_user.username,
            first_name=register_user.firstname,
            last_name=register_user.lastname,
            password=register_user.password,
            email=register_user.email,
        )

        user.save()
        register_user.delete()

        return Response(
            {
                'detail': 'User registered',
            },
            status=status.HTTP_200_OK,
        )

        

        


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

    
    

