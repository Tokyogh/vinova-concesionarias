# Generated for Vinova Pro v0.16

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vehicles", "0002_alter_vehicle_options_alter_vehiclebrand_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="internal_code",
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="vin",
            field=models.CharField(blank=True, db_index=True, max_length=40, null=True, unique=True),
        ),
    ]
