from django.contrib.auth import get_user_model
from django.db import transaction
from knox.models import AuthToken

from storyfinder.settings import _env

User = get_user_model()

class UserSetupService():
    def __init__(self):
        self.admin_password = _env('ADMIN_USER_PASSWORD')
        self.admin_token = _env('ADMIN_USER_TOKEN')
        self.test_password = _env('TEST_USER_PASSWORD')

    @transaction.atomic
    def reset_dev_environment(self):
        User.objects.all().delete()

    @transaction.atomic
    def setup_dev_environment(self):
        admins_to_create = [
            ('admin', 'Admin', 'User'),
            ('dani', 'Daniel', 'Pietsch'),
            ('steffen', 'Steffen', 'Remus'),
        ]

        for username, first_name, last_name in admins_to_create:
            admin, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@storyfinder.dev',
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_superuser': True,
                    'is_staff': True,
                },
            )

            if created:
                admin.set_password(self.admin_password)
                admin.save()

                if username == 'admin':
                    AuthToken.objects.get_or_create(user=admin)

        users_to_create = [
            ('User1', 'User', '1'),
            ('User2', 'User', '2'),
            ('User3', 'User', '3'),
            ('User4', 'User', '4'),
            ('User5', 'User', '5'),
            ('User6', 'User', '6'),
            ('User7', 'User', '7'),
            ('User8', 'User', '8'),
            ('User9', 'User', '9'),
            ('User10', 'User', '10'),
            ('User11', 'User', '11'),
            ('User12', 'User', '12'),
            ('User13', 'User', '13'),
            ('User14', 'User', '14'),
            ('User15', 'User', '15'),
            ('User16', 'User', '16'),
            ('User17', 'User', '17'),
            ('User18', 'User', '18'),
            ('User19', 'User', '19'),
            ('User20', 'User', '20'),

        ]

        for username, first_name, last_name in users_to_create:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@storyfinder.usr',
                    'first_name': first_name,
                    'last_name': last_name,
                },
            )
            
            if created:
                user.set_password(self.test_password)
                user.save()

        return len(admins_to_create) + len(users_to_create)