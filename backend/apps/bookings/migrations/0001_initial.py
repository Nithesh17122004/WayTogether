import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("journeys", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("seats_requested", models.PositiveSmallIntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(8),
                    ],
                )),
                ("request_message", models.CharField(blank=True, max_length=500)),
                ("driver_response", models.CharField(blank=True, max_length=500)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending driver response"),
                        ("confirmed", "Confirmed"),
                        ("declined", "Declined"),
                        ("cancelled", "Cancelled"),
                    ],
                    default="pending",
                    max_length=12,
                )),
                ("estimated_contribution_per_passenger", models.DecimalField(
                    decimal_places=2, default=Decimal("0.00"), max_digits=9,
                )),
                ("estimated_contribution_total", models.DecimalField(
                    decimal_places=2, default=Decimal("0.00"), max_digits=9,
                )),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="cancelled_journey_bookings",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("journey", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="bookings",
                    to="journeys.journey",
                )),
                ("passenger", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="journey_bookings",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ("-requested_at",)},
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.UniqueConstraint(
                condition=Q(status__in=("pending", "confirmed")),
                fields=("journey", "passenger"),
                name="one_active_booking_per_passenger_journey",
            ),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["journey", "status"], name="booking_journey_status_idx"),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["passenger", "status"], name="booking_passenger_status_idx"),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["status", "requested_at"], name="booking_status_requested_idx"),
        ),
    ]
