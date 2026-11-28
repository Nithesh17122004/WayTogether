from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("finance", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="RazorpayPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_id", models.CharField(max_length=64, unique=True)),
                ("payment_id", models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ("status", models.CharField(choices=[("created", "Order created"), ("captured", "Payment captured"), ("failed", "Payment failed")], default="created", max_length=16)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=11)),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("test_mode", models.BooleanField(default=True)),
                ("failure_reason", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("contribution", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="razorpay_payments", to="finance.passengercontribution")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(
            model_name="razorpaypayment",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "created")), fields=("contribution",), name="one_open_razorpay_order_per_share"),
        ),
        migrations.AddIndex(
            model_name="razorpaypayment",
            index=models.Index(fields=["status", "created_at"], name="razorpay_status_date_idx"),
        ),
    ]
