from django.core.management.base import BaseCommand
from users.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        defaults = [
            ("admin", "admin", User.Role.ADMIN, True),
            ("operator", "operator", User.Role.OPERATOR, False),
            ("viewer", "viewer", User.Role.VIEWER, False),
        ]
        for username, password, role, is_staff in defaults:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(username=username, password=password, role=role, is_staff=is_staff)
