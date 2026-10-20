from django.db import migrations


GARAGE_PERMISSIONS = [
    ("vehicles", "vehicles.link_codes", "Generar y revocar códigos de vinculación"),
    ("portal", "portal.access", "Acceso al portal del cliente"),
]

ROLE_PERMISSION_ADDITIONS = {
    "admin_sucursal": ["vehicles.link_codes"],
    "asesor_postventa": ["vehicles.link_codes"],
    "cliente": ["portal.access"],
}


def seed_garage_permissions(apps, schema_editor):
    PermissionCode = apps.get_model("accounts", "PermissionCode")
    Role = apps.get_model("accounts", "Role")
    for module, code, name in GARAGE_PERMISSIONS:
        PermissionCode.objects.update_or_create(code=code, defaults={"module": module, "name": name})
    for role_code, codes in ROLE_PERMISSION_ADDITIONS.items():
        role = Role.objects.filter(code=role_code).first()
        if role is None:
            continue
        existing = set(role.permissions.values_list("code", flat=True))
        to_add = [code for code in codes if code not in existing]
        if to_add:
            role.permissions.add(*PermissionCode.objects.filter(code__in=to_add))


def unseed_garage_permissions(apps, schema_editor):
    # No destructivo: nunca se borran códigos de permiso ni se retiran roles.
    pass


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_user_avatar_user_avatar_provider")]

    operations = [migrations.RunPython(seed_garage_permissions, unseed_garage_permissions)]