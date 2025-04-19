from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Sets up test data for the directory'

    def handle(self, *args, **kwargs):
        # Create superuser if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Created superuser'))

        # Load fixtures
        call_command('loaddata', 'initial_data')
        call_command('loaddata', 'sample_businesses')
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded test data'))