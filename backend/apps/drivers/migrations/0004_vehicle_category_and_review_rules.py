from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0003_private_driver_documents"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="vehicle_category",
            field=models.CharField(
                choices=[
                    ("two_wheeler", "Two-wheeler"),
                    ("four_wheeler", "Four-wheeler"),
                ],
                default="four_wheeler",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="vehicle_type",
            field=models.CharField(
                choices=[
                    ("motorcycle", "Motorcycle"),
                    ("scooter", "Scooter"),
                    ("hatchback", "Hatchback"),
                    ("sedan", "Sedan"),
                    ("suv", "SUV"),
                    ("muv", "MUV"),
                    ("other", "Other"),
                ],
                max_length=12,
            ),
        ),
    ]
