import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import apps.drivers.models
import apps.drivers.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DriverProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bio", models.CharField(blank=True, max_length=500)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("verification_status", models.CharField(
                    choices=[
                        ("draft", "Draft"),
                        ("pending", "Pending review"),
                        ("approved", "Approved"),
                        ("needs_resubmission", "Needs resubmission"),
                        ("suspended", "Suspended"),
                    ],
                    default="draft",
                    max_length=24,
                )),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="driver_profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.CreateModel(
            name="Vehicle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("registration_number", models.CharField(max_length=20, unique=True)),
                ("make", models.CharField(max_length=60)),
                ("model", models.CharField(max_length=60)),
                ("manufacture_year", models.PositiveSmallIntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1980),
                        django.core.validators.MaxValueValidator(2100),
                    ],
                )),
                ("colour", models.CharField(blank=True, max_length=40)),
                ("vehicle_type", models.CharField(
                    choices=[
                        ("hatchback", "Hatchback"),
                        ("sedan", "Sedan"),
                        ("suv", "SUV"),
                        ("muv", "MUV"),
                        ("other", "Other"),
                    ],
                    max_length=12,
                )),
                ("passenger_seats", models.PositiveSmallIntegerField(
                    default=3,
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(8),
                    ],
                )),
                ("private_use_attested", models.BooleanField(default=False)),
                ("verification_status", models.CharField(
                    choices=[
                        ("draft", "Draft"),
                        ("pending", "Pending review"),
                        ("approved", "Approved"),
                        ("needs_resubmission", "Needs resubmission"),
                        ("suspended", "Suspended"),
                    ],
                    default="draft",
                    max_length=24,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="vehicles",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="VerificationDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document_type", models.CharField(
                    choices=[
                        ("driver_license", "Driving licence"),
                        ("vehicle_registration", "Vehicle registration certificate"),
                        ("insurance", "Insurance certificate"),
                        ("pollution_certificate", "Pollution certificate"),
                        ("vehicle_photo", "Vehicle photograph"),
                    ],
                    max_length=32,
                )),
                ("file", models.FileField(
                    max_length=255,
                    upload_to=apps.drivers.models.private_document_upload_to,
                    validators=[apps.drivers.validators.validate_document_file],
                )),
                ("original_file_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=80)),
                ("file_size", models.PositiveIntegerField()),
                ("expiry_date", models.DateField(blank=True, null=True)),
                ("review_status", models.CharField(
                    choices=[
                        ("pending", "Pending review"),
                        ("approved", "Approved"),
                        ("rejected", "Rejected"),
                    ],
                    default="pending",
                    max_length=12,
                )),
                ("review_note", models.CharField(blank=True, max_length=500)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("is_current", models.BooleanField(default=True)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="driver_documents",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("reviewed_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="reviewed_driver_documents",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("vehicle", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="documents",
                    to="drivers.vehicle",
                )),
            ],
            options={"ordering": ("-uploaded_at",)},
        ),
        migrations.AddIndex(
            model_name="verificationdocument",
            index=models.Index(fields=["owner", "document_type", "is_current"], name="driver_doc_current_idx"),
        ),
        migrations.AddIndex(
            model_name="verificationdocument",
            index=models.Index(fields=["review_status", "is_current"], name="driver_doc_review_idx"),
        ),
    ]
