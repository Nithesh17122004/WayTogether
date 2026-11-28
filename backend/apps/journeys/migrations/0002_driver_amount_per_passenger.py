from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models
import django.core.validators


def backfill_driver_amount(apps, schema_editor):
    Journey = apps.get_model("journeys", "Journey")
    for journey in Journey.objects.all().iterator():
        old_total = (
            journey.fuel_expense
            + journey.toll_expense
            + journey.parking_expense
            + journey.other_expense
        )
        divisor = Decimal(journey.seats_offered + 1)
        journey.driver_amount_per_passenger = (
            old_total / divisor
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        journey.save(update_fields=["driver_amount_per_passenger"])


class Migration(migrations.Migration):
    dependencies = [
        ("journeys", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="journey",
            name="driver_amount_per_passenger",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=9,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
            ),
        ),
        migrations.RunPython(backfill_driver_amount, migrations.RunPython.noop),
    ]
