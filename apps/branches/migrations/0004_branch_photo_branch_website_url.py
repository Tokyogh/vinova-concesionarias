"""Añade presentación pública configurable por sede.

Adds configurable public presentation fields for each branch.
"""

import django.core.validators
from django.db import migrations, models

import apps.common.validators


class Migration(migrations.Migration):
    dependencies = [("branches", "0003_branch_public_directory_fields")]

    operations = [
        migrations.AddField(
            model_name="branch",
            name="photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="branches/photos/",
                validators=[
                    apps.common.validators.validate_upload_extension,
                    apps.common.validators.validate_upload_size,
                ],
            ),
        ),
        migrations.AddField(
            model_name="branch",
            name="website_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                validators=[django.core.validators.URLValidator(schemes=["http", "https"])],
            ),
        ),
    ]
