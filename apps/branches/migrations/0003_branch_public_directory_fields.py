from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("branches", "0002_alter_branch_options")]

    operations = [
        migrations.AlterField(
            model_name="branch",
            name="branch_type",
            field=models.CharField(
                choices=[
                    ("institution", "Institución afiliada"),
                    ("dealership", "Concesionaria"),
                    ("service_center", "Centro de atención"),
                    ("warehouse", "Bodega"),
                    ("office", "Oficina"),
                ],
                db_index=True,
                default="dealership",
                max_length=40,
            ),
        ),
        migrations.AddField(model_name="branch", name="province", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="branch", name="description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="branch", name="opening_hours", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="branch", name="services", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(
            model_name="branch",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                validators=[MinValueValidator(-90), MaxValueValidator(90)],
            ),
        ),
        migrations.AddField(
            model_name="branch",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                validators=[MinValueValidator(-180), MaxValueValidator(180)],
            ),
        ),
    ]
