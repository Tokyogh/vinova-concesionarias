from django.db import migrations, models
from django.db.models import Count, Q


def validate_existing_commercial_integrity(apps, schema_editor):
    SaleRecord = apps.get_model("sales", "SaleRecord")
    missing = list(SaleRecord.objects.filter(is_deleted=False, status="reserved", reserved_until__isnull=True).values_list("number", flat=True)[:20])
    duplicates = list(SaleRecord.objects.filter(
        is_deleted=False, vehicle_id__isnull=False, status__in=["reserved", "sold"],
    ).values("vehicle_id").annotate(total=Count("id")).filter(total__gt=1).values_list("vehicle_id", "total")[:20])
    problems = []
    if missing:
        problems.append("reservas sin vencimiento: " + ", ".join(missing))
    if duplicates:
        problems.append("unidades duplicadas: " + ", ".join(f"vehicle_id={pk} ({total})" for pk, total in duplicates))
    if problems:
        raise RuntimeError("Migración detenida; corrige los datos mediante un proceso auditado. " + " | ".join(problems))


class Migration(migrations.Migration):
    dependencies = [("sales", "0001_initial")]
    operations = [
        migrations.RunPython(validate_existing_commercial_integrity, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="salerecord",
            constraint=models.UniqueConstraint(
                fields=("vehicle",),
                condition=Q(vehicle__isnull=False, is_deleted=False, status__in=["reserved", "sold"]),
                name="unique_active_vehicle_commitment",
            ),
        ),
        migrations.AddConstraint(
            model_name="salerecord",
            constraint=models.CheckConstraint(
                condition=~Q(status="reserved") | Q(reserved_until__isnull=False),
                name="reserved_sale_requires_expiry",
            ),
        ),
    ]
