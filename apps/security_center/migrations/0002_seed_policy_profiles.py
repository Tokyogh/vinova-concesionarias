from django.db import migrations

def seed(apps, schema_editor):
    Policy = apps.get_model("security_center", "SecurityPolicy")
    Profile = apps.get_model("security_center", "UserSecurityProfile")
    User = apps.get_model("accounts", "User")
    Policy.objects.get_or_create(name="Política principal", defaults={"is_active": True})
    for user_id in User.objects.values_list("id", flat=True).iterator():
        Profile.objects.get_or_create(user_id=user_id)

class Migration(migrations.Migration):
    dependencies = [("security_center", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
