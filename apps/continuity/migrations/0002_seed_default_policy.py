from django.db import migrations


def seed_policy(apps, schema_editor):
    BackupPolicy = apps.get_model("continuity", "BackupPolicy")
    BackupPolicy.objects.get_or_create(
        name="Política principal",
        defaults={
            "is_active": True,
            "frequency": "daily",
            "retention_days": 30,
            "include_database": True,
            "include_media": True,
            "include_private": True,
            "external_copy_required": True,
            "notes": "Configura una copia externa y prueba la restauración periódicamente.",
        },
    )


class Migration(migrations.Migration):
    dependencies = [("continuity", "0001_initial")]
    operations = [migrations.RunPython(seed_policy, migrations.RunPython.noop)]
