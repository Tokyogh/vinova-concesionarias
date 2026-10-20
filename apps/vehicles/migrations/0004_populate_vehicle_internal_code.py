import re
import unicodedata

from django.db import migrations, models


def normalize(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")


def populate_internal_codes(apps, schema_editor):
    Vehicle = apps.get_model("vehicles", "Vehicle")
    for vehicle in Vehicle.objects.select_related("brand", "model").order_by("id").iterator():
        base = normalize(f"VIN-{vehicle.brand.name}-{vehicle.model.name}-{vehicle.year}")[:70].strip("-") or "VIN-VEHICULO"
        candidate = base
        counter = 2
        while Vehicle.objects.exclude(pk=vehicle.pk).filter(internal_code__iexact=candidate).exists():
            suffix = f"-{counter:02d}"
            candidate = f"{base[:80-len(suffix)]}{suffix}"
            counter += 1
        Vehicle.objects.filter(pk=vehicle.pk).update(internal_code=candidate, vin=(vehicle.vin or "").strip().upper() or None)


class Migration(migrations.Migration):
    dependencies = [("vehicles", "0003_vehicle_internal_code_alter_vehicle_vin")]

    operations = [
        migrations.RunPython(populate_internal_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="vehicle",
            name="internal_code",
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=80, unique=True),
        ),
    ]
