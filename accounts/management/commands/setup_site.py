# accounts/management/commands/setup_site.py
import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings

class Command(BaseCommand):
    help = 'Set up Site object for django-allauth based on environment'

    def handle(self, *args, **options):
        domain = getattr(settings, 'SITE_DOMAIN', '127.0.0.1:8000')
        name = getattr(settings, 'SITE_NAME', 'BizDirectory Local')
        
        # Update or create the site
        site, created = Site.objects.get_or_create(
            pk=settings.SITE_ID,
            defaults={
                'domain': domain,
                'name': name
            }
        )
        
        if not created:
            # Update existing site
            site.domain = domain
            site.name = name
            site.save()
            
        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f'{action} Site object: {name} at {domain}'
            )
        )
