from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from user.models import CustomUser

# Register your models here.

@admin.register(CustomUser)
class UserAdminOverload(UserAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login')


