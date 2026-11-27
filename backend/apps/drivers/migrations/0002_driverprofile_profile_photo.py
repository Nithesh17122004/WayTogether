from django.db import migrations, models

import apps.drivers.models
import apps.drivers.validators


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="driverprofile",
            name="profile_photo",
            field=models.FileField(
                blank=True,
                max_length=255,
                upload_to=apps.drivers.models.private_driver_photo_upload_to,
                validators=[apps.drivers.validators.validate_driver_profile_photo],
            ),
        ),
    ]
