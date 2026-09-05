# Phylo Distance Matrix

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `CAP / CLSI / ISO Standards`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Phylogenetic Distance Matrix Builder with enterprise security features:

- **Domain Lookup Engine**: Token overlap + substring scoring for biomedical term matching (p-distance, JC69, K2P, Neighbor-Joining, FASTA, Newick)
- **Batch CSV Processing**: Process CSV files with automatic query column detection
- **Multi-Agent Supervisor**: Orchestrates specialized workers (QC, Safety, Protocol Conformance) for task evaluation
- **Zero-PHI Outbound Guard**: Regex-based detection and redaction of protected health information (SSN, MRN, phone, email, DOB)
- **HMAC-SHA256 Audit Trail**: Cryptographically chained, tamper-evident logging
- **FastAPI REST API**: OpenAPI 3.1 endpoints with Prometheus metrics

---

## ⚙️ Key Modules

### Core Module (`phylo_dist.py`)
- **`lookup(query)`** — Domain-specific term matching with scoring. Returns top hits.
- **`process_csv(input, output)`** — Batch CSV processing with validation and path traversal protection.
- **`build_parser()`** — CLI argument parser construction.
- **`main(argv)`** — CLI entry point.

### Enterprise Agents (`agents/`)
- **`base.py`** — PHI guard, HMAC-SHA256 audit trail, security exceptions
- **`supervisor.py`** — Multi-agent orchestration and consensus building
- **`workers.py`** — Specialized evaluation workers (QC, Safety, Protocol)
- **`api.py`** — FastAPI REST endpoints
- **`metrics.py`** — Prometheus metrics collector
- **`models.py`** — Pydantic data models

---

## 💻 CLI Quickstart & Usage

### Installation
```bash
pip install fastapi uvicorn pydantic pytest
```

### Run the CLI
```bash
# Single lookup
python phylo_dist.py single jc69

# Batch CSV processing
python phylo_dist.py batch --input sample.csv --output results.csv

# Enterprise supervisor audit
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch processing via supervisor
python cli.py batch -i sample.csv -o results.csv

# Verify audit trail integrity
python cli.py verify-audit

# Launch REST API server
python cli.py serve --host 127.0.0.1 --port 8000
```

### API Endpoints
| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/api/audit` | POST | Submit task for evaluation |
| `/api/chat` | POST | Supervisory chat query |
| `/api/audit/logs` | GET | Retrieve audit trail |

---

## 🛡️ Security Features

* **Zero-PHI Outbound Guard:** Regex-based detection of SSNs, MRNs, phone numbers, emails, DOBs, and patient names. Raises `SecurityException` on detection.
* **PHI Redaction:** `PHIGuard.redact_phi()` replaces sensitive patterns with `[REDACTED_IDENTIFIER]`.
* **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs. Set `AUDIT_SECRET_KEY` environment variable in production.
* **Path Traversal Protection:** File operations restricted to working directory and system temp directory.
* **Input Validation:** CSV file size limits, empty file detection, header validation.

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Run with coverage:

```bash
pytest -v --tb=short
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 100
```

---

## 🐳 Container Deployment

```bash
docker build -t phylo-distance-matrix .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key phylo-distance-matrix
```

Or using Docker Compose:

```bash
AUDIT_SECRET_KEY=your-secret-key docker-compose up
```

---

## 📁 Project Structure

```
phylo-distance-matrix/
├── phylo_dist.py          # Core lookup and CSV processing
├── cli.py                 # CLI interface
├── simulator.py           # Stress testing simulator
├── enrichment.py          # Feature engines
├── agents/                # Enterprise agent framework
│   ├── base.py           # Security, PHI guard, audit trail
│   ├── supervisor.py     # Multi-agent orchestrator
│   ├── workers.py        # Specialized evaluation workers
│   ├── api.py            # FastAPI endpoints
│   ├── models.py         # Pydantic models
│   ├── metrics.py        # Prometheus metrics
│   ├── llm_factory.py    # LLM provider factory
│   ├── learning.py       # Bayesian calibration
│   └── streamer.py       # WebSocket telemetry
├── tests/                 # Test suite
├── web/                   # Operations console (HTML)
├── Dockerfile             # Container definition
├── docker-compose.yml     # Compose configuration
└── .github/workflows/     # CI/CD pipeline
```
