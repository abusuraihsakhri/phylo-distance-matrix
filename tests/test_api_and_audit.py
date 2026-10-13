"""API and audit authentication regression tests."""
import csv

from fastapi.testclient import TestClient

from agents.api import app
from agents.base import AuditTrail
from cli import main


def test_public_matrix_api_and_static_browser():
    client = TestClient(app)
    response = client.post("/api/matrix", json={
        "fasta": ">A\nACGT\n>B\nATGT\n",
        "model": "p",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["taxa"] == ["A", "B"]
    assert data["distances"] == [[0.0, 0.25], [0.25, 0.0]]
    assert client.get("/").status_code == 200
    assert "Phylogenetic Distance Matrix" in client.get("/").text
    assert client.get("/app.mjs").status_code == 200


def test_api_rejects_undefined_corrected_distances():
    client = TestClient(app)
    response = client.post("/api/matrix", json={"fasta": ">A\nAAAA\n>B\nTTTT\n", "model": "jc69"})
    assert response.status_code == 422
    assert "saturation" in response.json()["detail"]
    assert client.post("/api/matrix", json={"fasta": ">A\nACG\n>B\nACGT\n"}).status_code == 422


def test_audit_chain_detects_hmac_tampering():
    audit = AuditTrail(secret_key="test-key")
    audit.log("operator", "tier", "EVENT", {"outcome": "ok"})
    audit.log("operator", "tier", "EVENT2", {"outcome": "ok"})
    assert audit.verify_integrity()
    audit.get_trail()[0]["actor"] = "attacker"
    assert not audit.verify_integrity()
    audit.get_trail()[0]["actor"] = "operator"
    assert audit.verify_integrity()
    audit.get_trail()[1]["current_hash"] = "0" * 64
    assert not audit.verify_integrity()


def test_cli_batch_parses_false_boolean_correctly(tmp_path):
    source = tmp_path / "tasks.csv"
    target = tmp_path / "dossiers.csv"
    source.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,status_descriptor,is_critical_flag\n"
        "T1,KEY-1,0,0,NOMINAL,false\n"
        "T2,KEY-2,0,0,NOMINAL,true\n",
        encoding="utf-8",
    )
    assert main(["batch", "-i", str(source), "-o", str(target)]) == 0
    with target.open(newline="", encoding="utf-8") as handle:
        results = list(csv.DictReader(handle))
    assert results[0]["overall_urgency"] == "ROUTINE"
    assert results[1]["overall_urgency"] == "CRITICAL_STAT_PANIC"
