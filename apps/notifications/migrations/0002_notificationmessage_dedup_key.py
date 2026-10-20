from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="notificationmessage",
            name="dedup_key",
            field=models.CharField(blank=True, db_index=True, max_length=160),
        ),
        migrations.AddConstraint(
            model_name="notificationmessage",
            constraint=models.UniqueConstraint(
                condition=~models.Q(dedup_key=""),
                fields=("dedup_key",),
                name="unique_notification_dedup_key",
            ),
        ),
    ]
