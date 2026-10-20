# Generated for Vinova Pro v0.13 reportes empresariales

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportExportJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('report_type', models.CharField(choices=[('executive', 'Resumen ejecutivo'), ('sales', 'Ventas por fecha'), ('branches', 'Ventas por sucursal'), ('vehicles', 'Vehículos por estado'), ('inventory', 'Inventario bajo'), ('stock_movements', 'Movimientos de stock'), ('invoices', 'Facturas emitidas'), ('customers', 'Clientes nuevos'), ('activity', 'Actividad de usuarios'), ('products', 'Productos más vendidos')], db_index=True, max_length=40)),
                ('export_format', models.CharField(choices=[('csv', 'CSV'), ('xlsx', 'Excel'), ('print', 'Vista imprimible / PDF')], db_index=True, max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('running', 'En proceso'), ('completed', 'Completado'), ('failed', 'Fallido')], db_index=True, default='pending', max_length=20)),
                ('filters', models.JSONField(blank=True, default=dict)),
                ('row_count', models.PositiveIntegerField(default=0)),
                ('file_name', models.CharField(blank=True, max_length=180)),
                ('error_message', models.TextField(blank=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='report_exports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Exportación de reporte',
                'verbose_name_plural': 'Exportaciones de reportes',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['report_type', 'created_at'], name='reports_rep_report__fe9c43_idx'), models.Index(fields=['requested_by', 'status'], name='reports_rep_request_ab120c_idx'), models.Index(fields=['export_format', 'status'], name='reports_rep_export__1c4ec2_idx')],
            },
        ),
    ]
