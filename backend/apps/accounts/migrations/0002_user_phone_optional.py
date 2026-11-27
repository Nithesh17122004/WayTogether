import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=16,
                null=True,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Enter a mobile number in international format, such as +919876543210.",
                        regex=r"^\+[1-9]\d{7,14}$",
                    )
                ],
            ),
        ),
    ]
