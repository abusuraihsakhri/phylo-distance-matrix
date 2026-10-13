"""
FastAPI REST API Server for Phylo Distance Matrix.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from fastapi.responses import FileResponse
from typing import Literal
from distance_matrix import parse_fasta, calculate_matrix
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Phylo Distance Matrix API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class MatrixRequest(BaseModel):
    fasta: str = Field(..., min_length=1, max_length=2 * 1024 * 1024)
    model: Literal["p", "jc69", "k2p"] = "p"


@app.post("/api/matrix")
def api_matrix(request: MatrixRequest):
    """Calculate actual pairwise sequence distances (no disk storage)."""
    try:
        records = parse_fasta(request.fasta)
        if len(records) > 100 or len(records[0][1]) > 100000:
            raise ValueError("API limit: at most 100 taxa and 100,000 aligned columns")
        return {"taxa": [name for name, _ in records],
                "model": request.model,
                "distances": calculate_matrix(records, request.model)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "phylo-distance-matrix", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}


@app.get("/", include_in_schema=False)
def browser_index():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html")


@app.get("/app.mjs", include_in_schema=False)
def browser_script():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "app.mjs", media_type="text/javascript")
