import apps.drivers.models
import apps.drivers.storage
import apps.drivers.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0002_driverprofile_profile_photo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="driverprofile",
            name="profile_photo",
            field=models.FileField(
                blank=True,
                max_length=255,
                storage=apps.drivers.storage.get_private_driver_storage,
                upload_to=apps.drivers.models.private_driver_photo_upload_to,
                validators=[apps.drivers.validators.validate_driver_profile_photo],
            ),
        ),
        migrations.AlterField(
            model_name="verificationdocument",
            name="file",
            field=models.FileField(
                max_length=255,
                storage=apps.drivers.storage.get_private_driver_storage,
                upload_to=apps.drivers.models.private_document_upload_to,
                validators=[apps.drivers.validators.validate_document_file],
            ),
        ),
        migrations.AlterField(
            model_name="verificationdocument",
            name="document_type",
            field=models.CharField(
                choices=[
                    ("driver_license", "Driving licence"),
                    ("vehicle_registration", "Vehicle registration certificate"),
                    ("insurance", "Insurance certificate"),
                    ("pollution_certificate", "Pollution certificate"),
                    ("vehicle_photo", "Vehicle photograph"),
                    ("driver_photo", "Driver face photo"),
                ],
                max_length=32,
            ),
        ),
    ]
