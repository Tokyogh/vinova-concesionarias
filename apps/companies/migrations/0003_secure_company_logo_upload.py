import apps.common.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("companies", "0002_alter_company_options")]

    operations = [
        migrations.AlterField(
            model_name="company",
            name="logo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="company/logos/",
                validators=[
                    apps.common.validators.validate_upload_extension,
                    apps.common.validators.validate_upload_size,
                ],
            ),
        ),
    ]
