"""Restringe los colores de marca a valores RGB hexadecimales seguros.

Restrict brand colors to safe hexadecimal RGB values.
"""

from django.db import migrations, models

import apps.common.validators


class Migration(migrations.Migration):
    dependencies = [("companies", "0003_secure_company_logo_upload")]

    operations = [
        migrations.AlterField(
            model_name="company",
            name="primary_color",
            field=models.CharField(
                default="#0f3b66",
                max_length=20,
                validators=[apps.common.validators.validate_hex_color],
            ),
        ),
        migrations.AlterField(
            model_name="company",
            name="secondary_color",
            field=models.CharField(
                default="#f2f5f8",
                max_length=20,
                validators=[apps.common.validators.validate_hex_color],
            ),
        ),
    ]
