"""Alinea valores iniciales de contraseñas con ASVS sin sobrescribir políticas personalizadas.

Align password defaults with ASVS without overwriting customized policies.
"""

from django.db import migrations, models


def migrate_legacy_defaults(apps, schema_editor):
    """Update only untouched legacy defaults; preserve administrator choices."""

    SecurityPolicy = apps.get_model("security_center", "SecurityPolicy")
    SecurityPolicy.objects.filter(
        require_uppercase=True,
        require_lowercase=True,
        require_digit=True,
        require_symbol=True,
        password_max_age_days=90,
    ).update(
        require_uppercase=False,
        require_lowercase=False,
        require_digit=False,
        require_symbol=False,
        password_max_age_days=0,
    )


class Migration(migrations.Migration):
    dependencies = [("security_center", "0002_seed_policy_profiles")]

    operations = [
        migrations.AlterField(
            model_name="securitypolicy",
            name="password_max_age_days",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="securitypolicy",
            name="require_digit",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="securitypolicy",
            name="require_lowercase",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="securitypolicy",
            name="require_symbol",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="securitypolicy",
            name="require_uppercase",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(migrate_legacy_defaults, migrations.RunPython.noop),
    ]
