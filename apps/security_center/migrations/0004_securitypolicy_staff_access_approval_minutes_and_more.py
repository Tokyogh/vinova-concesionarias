"""Añade acceso Staff adaptativo y su permiso de aprobación independiente.

Add adaptive Staff access and its independent approval permission.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_staff_access_permission(apps, schema_editor):
    PermissionCode = apps.get_model("accounts", "PermissionCode")
    Role = apps.get_model("accounts", "Role")
    permission, _ = PermissionCode.objects.update_or_create(
        code="security.approve_staff_access",
        defaults={
            "module": "security",
            "name": "Aprobar acceso Staff excepcional",
            "description": "Decide solicitudes temporales de acceso Staff fuera de política.",
        },
    )
    for role in Role.objects.filter(code__in=("superadmin", "admin_general")):
        role.permissions.add(permission)


def unseed_staff_access_permission(apps, schema_editor):
    PermissionCode = apps.get_model("accounts", "PermissionCode")
    PermissionCode.objects.filter(code="security.approve_staff_access").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('security_center', '0003_password_policy_asvs_defaults'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='securitypolicy',
            name='staff_access_approval_minutes',
            field=models.PositiveSmallIntegerField(default=60),
        ),
        migrations.AddField(
            model_name='securitypolicy',
            name='staff_access_mode',
            field=models.CharField(choices=[('off', 'Desactivado'), ('monitor', 'Solo monitoreo'), ('enforce', 'Aplicar restricciones')], default='off', max_length=20),
        ),
        migrations.AddField(
            model_name='securitypolicy',
            name='staff_access_request_minutes',
            field=models.PositiveSmallIntegerField(default=15),
        ),
        migrations.AddField(
            model_name='securitypolicy',
            name='trusted_staff_networks',
            field=models.TextField(blank=True, help_text='IP/CIDR corporativas o de VPN, una por línea.'),
        ),
        migrations.CreateModel(
            name='StaffAccessRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session_reference', models.CharField(db_index=True, max_length=64)),
                ('ip_hash', models.CharField(db_index=True, max_length=64)),
                ('user_agent_hash', models.CharField(db_index=True, max_length=64)),
                ('risk_reasons', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('approved', 'Aprobada'), ('rejected', 'Rechazada'), ('revoked', 'Revocada'), ('expired', 'Expirada'), ('cancelled', 'Cancelada')], db_index=True, default='pending', max_length=20)),
                ('request_expires_at', models.DateTimeField(db_index=True)),
                ('access_expires_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('decision_note', models.CharField(blank=True, max_length=500)),
                ('decided_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='staff_access_decisions', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='staff_access_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Solicitud de acceso Staff',
                'verbose_name_plural': 'Solicitudes de acceso Staff',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user', 'status', '-created_at'], name='security_ce_user_id_270cba_idx'), models.Index(fields=['session_reference', 'ip_hash', 'status'], name='security_ce_session_fbd2b7_idx')],
                'constraints': [models.UniqueConstraint(condition=models.Q(('status', 'pending')), fields=('user', 'session_reference', 'ip_hash', 'user_agent_hash'), name='unique_pending_staff_access_context')],
            },
        ),
        migrations.RunPython(seed_staff_access_permission, unseed_staff_access_permission),
    ]
