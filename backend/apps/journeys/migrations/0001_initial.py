from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("drivers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Journey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origin_name", models.CharField(max_length=200)),
                ("origin_latitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("origin_longitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("destination_name", models.CharField(max_length=200)),
                ("destination_latitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("destination_longitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("travel_date", models.DateField(db_index=True)),
                ("departure_time", models.TimeField()),
                ("seats_offered", models.PositiveSmallIntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(8),
                    ],
                )),
                ("fuel_expense", models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ("toll_expense", models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ("parking_expense", models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ("other_expense", models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ("expense_note", models.CharField(blank=True, max_length=500)),
                ("description", models.CharField(blank=True, max_length=1000)),
                ("route_distance_km", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ("route_duration_minutes", models.PositiveIntegerField(blank=True, null=True)),
                ("route_geometry", models.JSONField(blank=True, default=list)),
                ("independently_planned", models.BooleanField(default=False)),
                ("expenses_only", models.BooleanField(default=False)),
                ("status", models.CharField(
                    choices=[
                        ("draft", "Draft"),
                        ("published", "Published"),
                        ("cancelled", "Cancelled"),
                        ("completed", "Completed"),
                    ],
                    default="draft",
                    max_length=12,
                )),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("driver", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="journeys",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("vehicle", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="journeys",
                    to="drivers.vehicle",
                )),
            ],
            options={
                "ordering": ("travel_date", "departure_time"),
            },
        ),
        migrations.CreateModel(
            name="JourneyStop",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveSmallIntegerField()),
                ("location_name", models.CharField(max_length=200)),
                ("latitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("longitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("journey", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="stops",
                    to="journeys.journey",
                )),
            ],
            options={"ordering": ("sequence",)},
        ),
        migrations.AddConstraint(
            model_name="journeystop",
            constraint=models.UniqueConstraint(
                fields=("journey", "sequence"),
                name="unique_journey_stop_sequence",
            ),
        ),
        migrations.AddIndex(
            model_name="journey",
            index=models.Index(fields=["status", "travel_date"], name="journey_status_date_idx"),
        ),
        migrations.AddIndex(
            model_name="journey",
            index=models.Index(fields=["driver", "status"], name="journey_driver_status_idx"),
        ),
        migrations.AddIndex(
            model_name="journey",
            index=models.Index(fields=["origin_latitude", "origin_longitude"], name="journey_origin_coords_idx"),
        ),
        migrations.AddIndex(
            model_name="journey",
            index=models.Index(fields=["destination_latitude", "destination_longitude"], name="journey_dest_coords_idx"),
        ),
    ]
