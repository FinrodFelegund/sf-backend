from django.contrib.auth import authenticate
from rest_framework import serializers
from user.models import CustomUser, RegisterUser

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
        ]

class UserDetailedSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
            'date_joined',
            'last_login',
        ]

        read_only_fields = ['date_joined', 'last_login']


class RegisterUserSerializer(serializers.Serializer):
    username = serializers.CharField()
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'}, trim_whitespace=False)
    email = serializers.EmailField()

    def validate(self, attrs):
        username = attrs.get('username', '')
        firstname = attrs.get('firstname', '')
        lastname = attrs.get('lastname', '')
        password = attrs.get('password', '')
        email = attrs.get('email', '')

        if not username or not firstname or not lastname or not password or not email:
            raise serializers.ValidationError('Invalid register data received')

        registerUser = RegisterUser(username=username, firstname=firstname, lastname=lastname, password=password, email=email)
        attrs['user'] = registerUser

        return attrs

class UnlockUserSerializer(serializers.Serializer):
    id = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'}, trim_whitespace=False)

    def validate(self, attrs):
        username = attrs.get('username', '')
        password = attrs.get('password', '')

        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError('Invalid username or password')
        
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled')
        
        attrs['user'] = user
        return attrs
    
class AuthTokenSerializer(serializers.Serializer):
    token = serializers.CharField
    user = UserDetailedSerializer()