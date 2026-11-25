import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("journeys", "0001_initial"),
        ("bookings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpenseSettlement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actual_fuel_expense", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("actual_toll_expense", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("actual_parking_expense", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("actual_other_expense", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("actual_expense_note", models.CharField(blank=True, max_length=1000)),
                ("eligible_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=11)),
                ("driver_share", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=11)),
                ("passenger_seat_count", models.PositiveSmallIntegerField(default=0)),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("is_finalized", models.BooleanField(default=False)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("driver", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="submitted_expense_settlements", to=settings.AUTH_USER_MODEL)),
                ("journey", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="expense_settlement", to="journeys.journey")),
            ],
            options={"ordering": ("-submitted_at",)},
        ),
        migrations.CreateModel(
            name="PassengerContribution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("seat_count", models.PositiveSmallIntegerField()),
                ("per_seat_amount", models.DecimalField(decimal_places=2, max_digits=11)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=11)),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("booking", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="final_contribution", to="bookings.booking")),
                ("passenger", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="final_journey_contributions", to=settings.AUTH_USER_MODEL)),
                ("settlement", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contributions", to="finance.expensesettlement")),
            ],
            options={"ordering": ("created_at", "id")},
        ),
        migrations.AddIndex(
            model_name="passengercontribution",
            index=models.Index(fields=["passenger", "created_at"], name="finance_passenger_date_idx"),
        ),
        migrations.AddIndex(
            model_name="passengercontribution",
            index=models.Index(fields=["settlement", "created_at"], name="finance_settlement_date_idx"),
        ),
        migrations.CreateModel(
            name="SandboxPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("provider", models.CharField(default="sandbox", editable=False, max_length=24)),
                ("status", models.CharField(choices=[("created", "Sandbox initiated"), ("succeeded", "Sandbox successful"), ("failed", "Sandbox failed"), ("refunded", "Sandbox refunded")], default="created", max_length=12)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=11)),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("failure_note", models.CharField(blank=True, max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("contribution", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sandbox_payments", to="finance.passengercontribution")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(
            model_name="sandboxpayment",
            constraint=models.UniqueConstraint(
                condition=Q(status__in=("created", "succeeded")),
                fields=("contribution",),
                name="one_active_sandbox_payment_per_share",
            ),
        ),
        migrations.AddIndex(
            model_name="sandboxpayment",
            index=models.Index(fields=["status", "created_at"], name="finance_payment_status_idx"),
        ),
        migrations.CreateModel(
            name="SandboxRefund",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=11)),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("reason", models.CharField(max_length=500)),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
                ("payment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="sandbox_refund", to="finance.sandboxpayment")),
                ("processed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="processed_sandbox_refunds", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
