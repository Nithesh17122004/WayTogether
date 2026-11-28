import apps.accounts.models
import apps.accounts.storage
import apps.accounts.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_passenger_verification"),
    ]

    operations = [
        migrations.AlterField(
            model_name="passengerverification",
            name="masked_aadhaar_document",
            field=models.FileField(
                max_length=255,
                storage=apps.accounts.storage.get_private_passenger_storage,
                upload_to=apps.accounts.models.private_passenger_upload_to,
                validators=[apps.accounts.validators.validate_masked_aadhaar_file],
            ),
        ),
        migrations.AlterField(
            model_name="passengerverification",
            name="passenger_photo",
            field=models.FileField(
                max_length=255,
                storage=apps.accounts.storage.get_private_passenger_storage,
                upload_to=apps.accounts.models.private_passenger_upload_to,
                validators=[apps.accounts.validators.validate_passenger_photo],
            ),
        ),
    ]
