from django.contrib.auth import get_user_model
from django.db import transaction
from knox.models import AuthToken

import env

User = get_user_model()

class UserSetupService():
    def __init__(self):
        self.admin_password = env.ADMIN_USER_PASSWORD
        self.admin_token = env.ADMIN_USER_TOKEN
        self.test_password = env.TEST_USER_PASSWORD

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
            ('John_Doe', 'John', 'Doe'),
            ('Sarah_Parker', 'Sarah', 'Parker'),
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