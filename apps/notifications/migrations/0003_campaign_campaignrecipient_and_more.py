import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("branches", "0002_alter_branch_options"),
        ("customers", "0001_initial"),
        ("notifications", "0002_notificationmessage_dedup_key"),
        ("privacy", "0002_seed_privacy_defaults_and_backfill_consents"),
        ("vehicles", "0004_populate_vehicle_internal_code"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Campaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(db_index=True, max_length=160)),
                ("status", models.CharField(choices=[("draft", "Borrador"), ("review", "En revisi\u00c3\u00b3n"), ("ready", "Lista para confirmar"), ("sent", "Enviada"), ("cancelled", "Cancelada")], db_index=True, default="draft", max_length=20)),
                ("segment_type", models.CharField(choices=[("all", "Todos los clientes"), ("recent", "Actividad reciente"), ("inactive", "Clientes inactivos"), ("buyers", "Compradores"), ("brand", "Inter\u00c3\u00a9s o compra por marca"), ("model", "Inter\u00c3\u00a9s o compra por modelo"), ("created_range", "Alta en rango de fechas"), ("service", "Clientes de postventa")], db_index=True, default="all", max_length=30)),
                ("inactivity_days", models.PositiveSmallIntegerField(default=90)),
                ("customer_created_from", models.DateField(blank=True, null=True)),
                ("customer_created_to", models.DateField(blank=True, null=True)),
                ("subject", models.CharField(blank=True, max_length=180)),
                ("body", models.TextField(blank=True)),
                ("channel", models.CharField(choices=[("in_app", "Notificaci\u00c3\u00b3n registrada")], default="in_app", max_length=20)),
                ("consent_purpose", models.CharField(choices=[("marketing", "Marketing"), ("commercial_contact", "Contacto comercial")], default="marketing", max_length=32)),
                ("recipient_count", models.PositiveIntegerField(default=0)),
                ("calculated_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notification_campaigns", to="branches.branch")),
                ("brand", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notification_campaigns", to="vehicles.vehiclebrand")),
                ("confirmed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="confirmed_campaigns", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_campaigns", to=settings.AUTH_USER_MODEL)),
                ("notification", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="campaign", to="notifications.notificationmessage")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_campaigns", to=settings.AUTH_USER_MODEL)),
                ("template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="campaigns", to="notifications.notificationtemplate")),
                ("vehicle_model", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notification_campaigns", to="vehicles.vehiclemodel")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CampaignRecipient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("display_name_snapshot", models.CharField(max_length=180)),
                ("email_snapshot", models.EmailField(blank=True, max_length=254)),
                ("phone_snapshot", models.CharField(blank=True, max_length=30)),
                ("rendered_subject", models.CharField(blank=True, max_length=180)),
                ("rendered_body", models.TextField(blank=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recipient_snapshots", to="notifications.campaign")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="campaign_snapshots", to="customers.customer")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddIndex(model_name="campaign", index=models.Index(fields=["branch", "status"], name="notificatio_branch__951136_idx")),
        migrations.AddIndex(model_name="campaign", index=models.Index(fields=["segment_type", "created_at"], name="notificatio_segment_261f13_idx")),
        migrations.AddIndex(model_name="campaignrecipient", index=models.Index(fields=["campaign", "created_at"], name="notificatio_campaig_efe766_idx")),
        migrations.AddConstraint(model_name="campaignrecipient", constraint=models.UniqueConstraint(fields=("campaign", "customer"), name="unique_campaign_customer_snapshot")),
    ]
