from django.db import migrations, models
from django.db.models import F, Q


def validate_reserved_stock(apps, schema_editor):
    BranchStock = apps.get_model("inventory", "BranchStock")
    alias = schema_editor.connection.alias
    invalid = BranchStock.objects.using(alias).filter(reserved_quantity__gt=F("quantity"))
    if invalid.exists():
        sample_ids = list(invalid.order_by("pk").values_list("pk", flat=True)[:20])
        raise RuntimeError(
            "No se puede aplicar stock_reserved_lte_quantity: existen registros "
            f"BranchStock con reserva superior al stock. IDs de muestra: {sample_ids}"
        )


class Migration(migrations.Migration):
    dependencies = [("inventory", "0001_initial")]

    operations = [
        migrations.RunPython(validate_reserved_stock, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="branchstock",
            constraint=models.CheckConstraint(
                condition=Q(reserved_quantity__lte=F("quantity")),
                name="stock_reserved_lte_quantity",
            ),
        ),
    ]
