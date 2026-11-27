import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create or promote the configured WayTogether platform administrator."

    def handle(self, *args, **options):
        email = os.getenv("WAYTOGETHER_BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
        password = os.getenv("WAYTOGETHER_BOOTSTRAP_ADMIN_PASSWORD", "")

        if not email and not password:
            self.stdout.write("Admin bootstrap skipped; no bootstrap credentials configured.")
            return
        if not email or not password:
            raise CommandError(
                "Both WAYTOGETHER_BOOTSTRAP_ADMIN_EMAIL and "
                "WAYTOGETHER_BOOTSTRAP_ADMIN_PASSWORD must be configured."
            )
        if len(password) < 10:
            raise CommandError("The bootstrap administrator password must be at least 10 characters.")

        with transaction.atomic():
            user = User.objects.filter(email__iexact=email).first()
            created = user is None

            if created:
                user = User(email=email)

            user.role = User.Role.ADMIN
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
            user.is_email_verified = True

            # Set the supplied password on creation or when it differs. Once the
            # bootstrap variables are removed from Render, normal password
            # changes will no longer be affected by this command.
            if created or not user.check_password(password):
                user.set_password(password)

            user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Platform administrator {'created' if created else 'updated'}: {email}"
            )
        )
