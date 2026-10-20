"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for models in the deployment_smoke helpers domain.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from tests.deployment_smoke import SOURCE_VERSION

STATUSES = {"passed", "warning", "failed", "skipped"}
RUN_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")


@dataclass
class CheckResult:
    code: str
    scenario: str
    title: str
    status: str
    message: str
    duration_seconds: float = 0.0
    required: bool = True
    evidence: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"Estado de control inválido: {self.status}")


@dataclass
class CreatedResource:
    kind: str
    label: str
    detail_url: str
    cleanup_action: str
    cleanup_button: str
    cleaned: bool = False


@dataclass
class SmokeConfig:
    base_url: str
    mode: str
    scenarios: list[str]
    username: str = ""
    password: str = ""
    browser: str = "chromium"
    headless: bool = True
    timeout_seconds: int = 30
    retries: int = 1
    report_root: Path = Path("private/qa_reports")
    write_tests: bool = False
    cleanup: bool = False
    retain_demo_data: bool = False
    record_video: bool = False
    allow_http_local: bool = False
    verify_tls: bool = True
    demo_confirmation: str = ""
    retain_confirmation: str = ""
    role_credentials_file: Path | None = None
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def marker(self) -> str:
        return f"SMOKE-{self.run_id}"

    @property
    def hostname(self) -> str:
        return (urlparse(self.base_url).hostname or "").lower()

    @property
    def report_dir(self) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        return self.report_root / f"deployment-smoke-{timestamp}-{self.run_id}"


@dataclass
class RunState:
    config: SmokeConfig
    output_dir: Path
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_monotonic: float = field(default_factory=time.monotonic)
    checks: list[CheckResult] = field(default_factory=list)
    resources: list[CreatedResource] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    exit_code: int = 0

    def add(self, result: CheckResult) -> CheckResult:
        self.checks.append(result)
        return result

    def register_resource(self, resource: CreatedResource) -> None:
        self.resources.append(resource)

    def counts(self) -> dict[str, int]:
        return {status: sum(check.status == status for check in self.checks) for status in STATUSES}

    def deployment_ready(self) -> bool:
        return not any(
            check.status == "failed" or (check.required and check.status == "skipped")
            for check in self.checks
        )

    def status(self) -> str:
        if not self.deployment_ready():
            return "failed"
        if any(check.status == "warning" for check in self.checks):
            return "warning"
        return "passed"

    def summary(self) -> dict[str, Any]:
        completed = datetime.now(UTC)
        counts = self.counts()
        return {
            "schema_version": 1,
            "run_id": self.config.run_id,
            "source_version": SOURCE_VERSION,
            "mode": self.config.mode,
            "target_url": self.config.base_url,
            "target_host": self.config.hostname,
            "status": self.status(),
            "deployment_ready": self.deployment_ready(),
            "started_at": self.started_at.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": round(time.monotonic() - self.started_monotonic, 3),
            "counts": {
                "passed": counts["passed"],
                "warning": counts["warning"],
                "failed": counts["failed"],
                "skipped": counts["skipped"],
            },
            "selected_scenarios": self.config.scenarios,
            "write_tests": self.config.write_tests,
            "tls_verification": self.config.verify_tls,
            "cleanup_requested": self.config.cleanup,
            "resources": [asdict(resource) for resource in self.resources],
            "checks": [asdict(check) for check in self.checks],
            "metadata": self.metadata,
            "exit_code": self.exit_code,
        }

    def write_summary(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / "summary.json"
        path.write_text(json.dumps(self.summary(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
