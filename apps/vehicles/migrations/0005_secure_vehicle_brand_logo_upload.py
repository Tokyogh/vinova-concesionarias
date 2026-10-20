import apps.common.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("vehicles", "0004_populate_vehicle_internal_code")]

    operations = [
        migrations.AlterField(
            model_name="vehiclebrand",
            name="logo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="vehicles/brands/",
                validators=[
                    apps.common.validators.validate_upload_extension,
                    apps.common.validators.validate_upload_size,
                ],
            ),
        ),
    ]
