import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Automatically creates a Super user'

    def handle(self, *args, **options):
        try:
            UserModel = get_user_model()
            username = os.getenv('DJANGO_SUPERUSER_USERNAME')
            email = os.getenv('DJANGO_SUPERUSER_EMAIL')
            password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

            success_message = 'Super User created.'
            if not UserModel.objects.filter(username=username).exists():
                UserModel.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(self.style.SUCCESS(success_message))
            else:
                warning_msg = "That user already exists."
                self.stdout.write(self.style.WARNING(warning_msg))
        except Exception as e:
            self.stdout.write(self.style.ERROR(str(e)))
            raise CommandError("Error creating super user")