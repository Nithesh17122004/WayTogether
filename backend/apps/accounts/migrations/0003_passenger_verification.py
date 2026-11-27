import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.accounts.models
import apps.accounts.validators


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_phone_optional"),
    ]

    operations = [
        migrations.CreateModel(
            name="PassengerVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("masked_aadhaar_document", models.FileField(
                    max_length=255,
                    upload_to=apps.accounts.models.private_passenger_upload_to,
                    validators=[apps.accounts.validators.validate_masked_aadhaar_file],
                )),
                ("passenger_photo", models.FileField(
                    max_length=255,
                    upload_to=apps.accounts.models.private_passenger_upload_to,
                    validators=[apps.accounts.validators.validate_passenger_photo],
                )),
                ("masked_aadhaar_file_name", models.CharField(max_length=255)),
                ("passenger_photo_file_name", models.CharField(max_length=255)),
                ("consent_at", models.DateTimeField()),
                ("status", models.CharField(
                    choices=[("pending", "Pending review"), ("approved", "Approved"), ("rejected", "Rejected")],
                    default="pending",
                    max_length=12,
                )),
                ("review_note", models.CharField(blank=True, max_length=500)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("submitted_at", models.DateTimeField(auto_now=True)),
                ("reviewed_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="reviewed_passenger_verifications",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="passenger_verification",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ("submitted_at",)},
        ),
        migrations.AddIndex(
            model_name="passengerverification",
            index=models.Index(fields=["status", "submitted_at"], name="passenger_kyc_queue_idx"),
        ),
    ]
