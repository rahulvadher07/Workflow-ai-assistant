from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Creates the initial Super Admin account (role=SUPER_ADMIN, status=ACTIVE)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--first-name", default="Super")
        parser.add_argument("--last-name", default="Admin")

    def handle(self, *args, **options):
        username = options["username"]

        if User.objects.filter(username=username).exists():
            raise CommandError(f"A user with username '{username}' already exists.")

        with transaction.atomic():
            user = User(
                username=username,
                email=options["email"],
                first_name=options["first_name"],
                last_name=options["last_name"],
                role=User.Role.SUPER_ADMIN,
                status=User.Status.ACTIVE,
                is_staff=True,
                is_superuser=True,
            )
            user.set_password(options["password"])
            user.save()

        self.stdout.write(self.style.SUCCESS(f"Super Admin '{username}' created successfully."))
