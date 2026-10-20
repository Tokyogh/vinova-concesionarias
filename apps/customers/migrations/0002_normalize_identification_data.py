from django.db import migrations


def forwards(apps, schema_editor):
    from apps.customers.identification import normalize_identification_data

    Customer = apps.get_model("customers", "Customer")
    normalize_identification_data(Customer)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
