import hashlib
import json
import uuid

import django.utils.timezone
from django.db import migrations, models


def infer(action):
    if action in {"login.success", "login.failed", "logout"}:
        category = "authentication"
    elif action.startswith("documents."):
        category = "document"
    elif action.startswith("inventory."):
        category = "inventory"
    elif action.startswith(("sales.", "invoices.")):
        category = "sales"
    elif action.startswith("imports."):
        category = "import"
    elif action.startswith(("enterprise.", "sri.")):
        category = "configuration"
    elif action.startswith("reports."):
        category = "report"
    elif action.startswith("accounts."):
        category = "authorization"
    else:
        category = "data_change"
    severity = "medium" if any(word in action for word in ("delete", "archive", "void", "password", "permission", "role")) else "info"
    return category, severity


def digest(payload):
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def populate_audit_integrity(apps, schema_editor):
    AuditLog = apps.get_model("audit", "AuditLog")
    previous_hash = ""
    for log in AuditLog.objects.select_related("user").order_by("created_at", "id").iterator():
        event_id = uuid.uuid4()
        occurred_at = log.created_at
        username = getattr(log.user, "username", "") if log.user_id else ""
        display = ""
        if log.user_id:
            display = (f"{getattr(log.user, 'first_name', '')} {getattr(log.user, 'last_name', '')}").strip() or username
        category, severity = infer(log.action)
        payload = {
            "event_id": str(event_id),
            "occurred_at": occurred_at.isoformat(),
            "user_id": log.user_id,
            "action": log.action,
            "category": category,
            "severity": severity,
            "result": "success",
            "object": [log.content_type_label, log.object_id],
            "request_id": "",
            "before": log.before,
            "after": log.after,
            "metadata": log.metadata,
            "previous_hash": previous_hash,
        }
        entry_hash = digest(payload)
        AuditLog.objects.filter(pk=log.pk).update(
            event_id=event_id,
            occurred_at=occurred_at,
            username_snapshot=username,
            user_display_snapshot=display,
            branch_id=getattr(log.user, "branch_id", None) if log.user_id else None,
            category=category,
            severity=severity,
            result="success",
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        previous_hash = entry_hash


class Migration(migrations.Migration):
    dependencies = [("audit", "0003_securityalert_alter_auditlog_options_and_more")]

    operations = [
        migrations.RunPython(populate_audit_integrity, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="auditlog",
            name="entry_hash",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="event_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="occurred_at",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
    ]
