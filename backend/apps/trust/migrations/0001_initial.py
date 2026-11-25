import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("bookings", "0001_initial"),
        ("journeys", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmergencyContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("contact_name", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=16, validators=[django.core.validators.RegexValidator(message="Enter an international-format phone number, such as +919876543210.", regex="^\\+[1-9]\\d{7,14}$")])),
                ("relationship", models.CharField(blank=True, max_length=80)),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="emergency_contacts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-is_primary", "contact_name")},
        ),
        migrations.AddConstraint(
            model_name="emergencycontact",
            constraint=models.UniqueConstraint(fields=("user", "phone"), name="trust_unique_emergency_phone"),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[
                    ("booking_request", "Booking request"),
                    ("booking_confirmed", "Booking confirmed"),
                    ("booking_declined", "Booking declined"),
                    ("booking_cancelled", "Booking cancelled"),
                    ("journey_cancelled", "Journey cancelled"),
                    ("new_message", "New message"),
                    ("expense_finalized", "Expenses finalized"),
                    ("safety_update", "Safety report update"),
                ], max_length=32)),
                ("title", models.CharField(max_length=160)),
                ("body", models.CharField(max_length=500)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sent_activity_notifications", to=settings.AUTH_USER_MODEL)),
                ("booking", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notifications", to="bookings.booking")),
                ("journey", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notifications", to="journeys.journey")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activity_notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "read_at", "-created_at"], name="trust_notify_inbox_idx"),
        ),
        migrations.CreateModel(
            name="BookingMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.CharField(max_length=1500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="messages", to="bookings.booking")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="booking_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("created_at", "id")},
        ),
        migrations.AddIndex(
            model_name="bookingmessage",
            index=models.Index(fields=["booking", "created_at"], name="trust_message_thread_idx"),
        ),
        migrations.CreateModel(
            name="SafetyReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[
                    ("unsafe_driving", "Unsafe driving"),
                    ("harassment", "Harassment or inappropriate behaviour"),
                    ("misrepresentation", "Profile or journey misrepresentation"),
                    ("payment_dispute", "Expense contribution dispute"),
                    ("accident", "Accident or injury"),
                    ("other", "Other safety concern"),
                ], max_length=24)),
                ("priority", models.CharField(choices=[("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")], default="normal", max_length=8)),
                ("description", models.TextField(max_length=5000)),
                ("status", models.CharField(choices=[("open", "Open"), ("reviewing", "Under review"), ("resolved", "Resolved"), ("closed", "Closed")], default="open", max_length=12)),
                ("admin_note", models.CharField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_safety_reports", to=settings.AUTH_USER_MODEL)),
                ("booking", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="safety_reports", to="bookings.booking")),
                ("journey", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="safety_reports", to="journeys.journey")),
                ("reported_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="safety_reports_about_user", to=settings.AUTH_USER_MODEL)),
                ("reporter", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="submitted_safety_reports", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="safetyreport",
            index=models.Index(fields=["status", "priority", "-created_at"], name="trust_report_queue_idx"),
        ),
        migrations.AddIndex(
            model_name="safetyreport",
            index=models.Index(fields=["reporter", "-created_at"], name="trust_report_owner_idx"),
        ),
        migrations.CreateModel(
            name="JourneyReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("comment", models.CharField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reviews", to="bookings.booking")),
                ("reviewee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journey_reviews_received", to=settings.AUTH_USER_MODEL)),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journey_reviews_written", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(
            model_name="journeyreview",
            constraint=models.UniqueConstraint(fields=("booking", "reviewer"), name="trust_one_review_per_reviewer_booking"),
        ),
        migrations.AddIndex(
            model_name="journeyreview",
            index=models.Index(fields=["reviewee", "-created_at"], name="trust_reviewee_rating_idx"),
        ),
    ]
