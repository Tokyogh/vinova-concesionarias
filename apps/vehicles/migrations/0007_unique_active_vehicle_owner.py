from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("vehicles", "0006_vehiclelinkcode_customervehicle_and_more")]

    operations = [
        migrations.AddConstraint(
            model_name="customervehicle",
            constraint=models.UniqueConstraint(
                fields=("vehicle",),
                condition=models.Q(is_active=True, role_type="owner"),
                name="unique_active_vehicle_owner",
            ),
        ),
    ]
