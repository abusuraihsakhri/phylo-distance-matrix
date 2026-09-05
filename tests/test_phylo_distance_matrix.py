"""
Automated Pytest Test Suite for Phylo Distance Matrix.
Domain: Clinical & Biomedical AI
Standard: CAP / CLSI / ISO Standards
"""
import os
import sys
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, AuditTrail, SecurityException
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from agents.metrics import SystemMetricsCollector, GLOBAL_METRICS
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_phi_guard_redact():
    """Test that PHI patterns are properly redacted."""
    redacted = PHIGuard.redact_phi("Patient MRN-123456 has phone 555-123-4567")
    assert "MRN-123456" not in redacted
    assert "555-123-4567" not in redacted
    assert "[REDACTED_IDENTIFIER]" in redacted


def test_phi_guard_redact_email():
    """Test that email addresses are properly redacted."""
    redacted = PHIGuard.redact_phi("Contact user@example.com for details")
    assert "user@example.com" not in redacted
    assert "[REDACTED_IDENTIFIER]" in redacted


def test_phi_guard_redact_ssn():
    """Test that SSN patterns are properly redacted."""
    redacted = PHIGuard.redact_phi("SSN: 123-45-6789 is on file")
    assert "123-45-6789" not in redacted
    assert "[REDACTED_IDENTIFIER]" in redacted


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_audit_trail_without_secret_key_warns():
    """Test that creating AuditTrail without secret key emits a warning."""
    # Make sure env var is not set
    original = os.environ.pop("AUDIT_SECRET_KEY", None)
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            trail = AuditTrail()
            # Check that a RuntimeWarning was emitted
            runtime_warnings = [x for x in w if issubclass(x.category, RuntimeWarning)]
            assert len(runtime_warnings) >= 1
            assert "AUDIT_SECRET_KEY" in str(runtime_warnings[0].message)
    finally:
        if original is not None:
            os.environ["AUDIT_SECRET_KEY"] = original


def test_audit_trail_with_secret_key_no_warning():
    """Test that providing secret key directly does not emit a warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        trail = AuditTrail(secret_key="my-test-secret-key")
        runtime_warnings = [x for x in w if issubclass(x.category, RuntimeWarning)]
        assert len(runtime_warnings) == 0


def test_metrics_collector():
    """Test that metrics collector records and exports correctly."""
    collector = SystemMetricsCollector()
    collector.record_task("ROUTINE", 0.1)
    collector.record_task("ELEVATED_RISK", 0.2)
    collector.record_task("CRITICAL_STAT_PANIC", 0.3)
    collector.record_phi_block()

    assert collector.tasks_total == 3
    assert collector.routine_tasks_total == 1
    assert collector.elevated_alerts_total == 1
    assert collector.critical_alerts_total == 1
    assert collector.phi_blocks_total == 1

    prometheus_output = collector.export_prometheus_text()
    assert "system_tasks_total" in prometheus_output
    assert "alerts_triggered_total" in prometheus_output
    assert "phi_outbound_blocks_total" in prometheus_output
