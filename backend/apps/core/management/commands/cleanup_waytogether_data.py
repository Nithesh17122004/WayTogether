from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Keep administrators and future published journeys (plus their required "
        "driver/profile/vehicle records); remove other WayTogether app data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Delete the data listed in the summary. Without this flag the command is a dry run.",
        )

    @staticmethod
    def _count(app_label, model_name):
        return apps.get_model(app_label, model_name).objects.count()

    @staticmethod
    def _schedule_file_deletion(queryset, field_names):
        """Delete stored uploads only after the database transaction commits."""
        files = []
        for row in queryset.iterator():
            for field_name in field_names:
                file_field = getattr(row, field_name, None)
                if file_field and file_field.name:
                    files.append(file_field)
        return files

    def _delete_files_after_commit(self, files):
        def delete_files():
            for file_field in files:
                try:
                    file_field.delete(save=False)
                except Exception as exc:
                    self.stderr.write(self.style.WARNING(
                        f"Could not delete an uploaded file ({file_field.name}): {exc}"
                    ))
        transaction.on_commit(delete_files)

    def handle(self, *args, **options):
        User = apps.get_model("accounts", "User")
        Journey = apps.get_model("journeys", "Journey")
        Vehicle = apps.get_model("drivers", "Vehicle")
        DriverProfile = apps.get_model("drivers", "DriverProfile")
        today = timezone.localdate()
        now_time = timezone.localtime().time().replace(tzinfo=None)

        upcoming = Journey.objects.filter(status="published").filter(
            Q(travel_date__gt=today)
            | Q(travel_date=today, departure_time__gte=now_time)
        )
        journey_ids = list(upcoming.values_list("id", flat=True))
        vehicle_ids = set(upcoming.values_list("vehicle_id", flat=True))
        driver_ids = set(upcoming.values_list("driver_id", flat=True))
        vehicle_owner_ids = set(
            Vehicle.objects.filter(pk__in=vehicle_ids).values_list("owner_id", flat=True)
        )
        required_driver_ids = driver_ids | vehicle_owner_ids

        admins = User.objects.filter(
            Q(role="admin") | Q(is_staff=True) | Q(is_superuser=True)
        )
        admin_ids = set(admins.values_list("id", flat=True))
        if options["execute"] and not admin_ids:
            raise CommandError(
                "No admin/staff/superuser account was found. Refusing to delete user accounts."
            )
        keep_user_ids = admin_ids | required_driver_ids

        VerificationDocument = apps.get_model("drivers", "VerificationDocument")
        keep_document_ids = set(
            VerificationDocument.objects.filter(
                owner_id__in=required_driver_ids,
                is_current=True,
                review_status="approved",
            ).filter(
                Q(vehicle__isnull=True) | Q(vehicle_id__in=vehicle_ids)
            ).values_list("id", flat=True)
        )

        summary = [
            ("Administrator accounts to preserve", len(admin_ids)),
            ("Future published journeys to preserve", len(journey_ids)),
            ("Journey driver / vehicle-owner accounts required", len(required_driver_ids)),
            ("Other user accounts to remove", User.objects.exclude(pk__in=keep_user_ids).count()),
            ("Non-upcoming journeys to remove", Journey.objects.exclude(pk__in=journey_ids).count()),
            ("Bookings to remove", self._count("bookings", "Booking")),
            ("Expense settlements and payment records to remove",
             self._count("finance", "ExpenseSettlement")
             + self._count("finance", "PassengerContribution")
             + self._count("finance", "SandboxPayment")
             + self._count("finance", "SandboxRefund")
             + self._count("finance", "RazorpayPayment")),
            ("Messages, notifications, contacts, reports and reviews to remove",
             sum(self._count("trust", name) for name in (
                 "BookingMessage", "Notification", "EmergencyContact",
                 "SafetyReport", "JourneyReview",
             ))),
            ("Passenger verification submissions to remove",
             self._count("accounts", "PassengerVerification")),
            ("Non-current / unapproved / unrelated driver documents to remove",
             VerificationDocument.objects.exclude(pk__in=keep_document_ids).count()),
            ("Non-retained driver profiles to remove",
             DriverProfile.objects.exclude(user_id__in=required_driver_ids).count()),
            ("Vehicles not used by retained journeys to remove",
             Vehicle.objects.exclude(pk__in=vehicle_ids).count()),
        ]

        self.stdout.write(self.style.WARNING(
            "DRY RUN — nothing has been deleted."
            if not options["execute"]
            else "EXECUTING — this cleanup is destructive and cannot be undone here."
        ))
        for label, count in summary:
            self.stdout.write(f"{label}: {count}")

        if not options["execute"]:
            self.stdout.write(self.style.NOTICE(
                "Review these counts and take a Render PostgreSQL backup before running "
                "again with --execute."
            ))
            return

        with transaction.atomic():
            apps.get_model("finance", "RazorpayPayment").objects.all().delete()
            apps.get_model("finance", "SandboxRefund").objects.all().delete()
            apps.get_model("finance", "SandboxPayment").objects.all().delete()
            apps.get_model("finance", "PassengerContribution").objects.all().delete()
            apps.get_model("finance", "ExpenseSettlement").objects.all().delete()

            for model_name in (
                "BookingMessage", "JourneyReview", "SafetyReport",
                "Notification", "EmergencyContact",
            ):
                apps.get_model("trust", model_name).objects.all().delete()
            apps.get_model("bookings", "Booking").objects.all().delete()

            PassengerVerification = apps.get_model("accounts", "PassengerVerification")
            VerificationDocument = apps.get_model("drivers", "VerificationDocument")
            VerificationCode = apps.get_model("accounts", "VerificationCode")

            passenger_files = self._schedule_file_deletion(
                PassengerVerification.objects.all(),
                ("masked_aadhaar_document", "passenger_photo"),
            )
            documents_to_remove = VerificationDocument.objects.exclude(
                pk__in=keep_document_ids
            )
            document_files = self._schedule_file_deletion(
                documents_to_remove, ("file",)
            )
            profile_files = self._schedule_file_deletion(
                DriverProfile.objects.exclude(user_id__in=required_driver_ids),
                ("profile_photo",),
            )

            PassengerVerification.objects.all().delete()
            VerificationCode.objects.all().delete()
            documents_to_remove.delete()

            Journey.objects.exclude(pk__in=journey_ids).delete()
            Vehicle.objects.exclude(pk__in=vehicle_ids).delete()
            DriverProfile.objects.exclude(user_id__in=required_driver_ids).delete()
            User.objects.exclude(pk__in=keep_user_ids).delete()

            self._delete_files_after_commit(
                passenger_files + document_files + profile_files
            )

        self.stdout.write(self.style.SUCCESS(
            f"Cleanup complete. Preserved {len(admin_ids)} admin account(s), "
            f"{len(journey_ids)} future published journey(s), and "
            f"{len(required_driver_ids)} journey driver / vehicle-owner account(s)."
        ))
