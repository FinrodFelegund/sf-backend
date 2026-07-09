from django.core.management.base import BaseCommand
from user.services.user_setup import UserSetupService
from chat.services.prompt_setup import SystemPromptSetupService

class Command(BaseCommand):
    help = 'Complete project setup, creates admins and test users'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Wipe data and users first')

    def handle(self, *args, **options):

        user_service = UserSetupService()
        chat_service = SystemPromptSetupService()

        if options['reset']:
            user_service.reset_dev_environment()
            chat_service.reset_dev_environment()

        count = user_service.setup_dev_environment()
        self.stdout.write(self.style.SUCCESS(f'Successfully set up {count} users/admins'))

        count = chat_service.setup_dev_environment()
        self.stdout.write(self.style.SUCCESS(f'Successfully set up {count} system prompts'))