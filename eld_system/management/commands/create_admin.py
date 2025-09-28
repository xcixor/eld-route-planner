import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from eld_system.models import Driver, Vehicle


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
                admin = UserModel.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                Driver.objects.create(
                    user=admin.pk,
                    driver_number='ADMIN001',
                    initials='AD',
                    home_operating_center='Headquarters',
                    license_number='ADMIN123456',
                    license_state='IL'
                )
                Vehicle.objects.create(
                    vehicle_number='ADMINV001',
                    vehicle_type='truck',
                    make='FREIGHTLINER',
                    model='CASCADIA',
                    year=2007,
                    vin='1ADMINVIN123456789'
                )
                self.stdout.write(self.style.SUCCESS(success_message))
            else:
                warning_msg = "That user already exists."
                self.stdout.write(self.style.WARNING(warning_msg))

        except Exception as e:
            self.stdout.write(self.style.ERROR(str(e)))
            raise CommandError("Error creating super user")