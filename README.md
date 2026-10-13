# Phylogenetic Distance Matrix

A browser and Python utility for calculating pairwise nucleotide distances from **already aligned FASTA** sequences. Implements uncorrected p-distance, Jukes–Cantor (JC69), and Kimura 2-parameter (K2P) distances.

## Browser application

Open the static application in `web/` through a local web server or GitHub Pages (deployment configured in `.github/workflows/pages.yml`).

Paste an aligned DNA FASTA file or upload a `.fa` or `.fasta` file, select a model, and choose **Calculate matrix**. Inspect the symmetric matrix and download **CSV** or **PHYLIP**. **Load example** provides a small demonstration.

All browser calculations occur locally using JavaScript; the static app does **not** transmit sequences to an API. No Pyodide or backend is needed. Browser limits: 2 MB per input file, 100 taxa and 100,000 alignment columns. Modern browsers supporting ES modules, the File API and Blob downloads are required.

## Distance models

For a pair of sequences, let \(L\) be the number of columns where both contain unambiguous A, C, G, or T. Ambiguous IUPAC bases, gaps and missing positions are **pairwise deleted**.

- **p-distance:** \(p = (\mathrm{transitions}+\mathrm{transversions})/L\).
- **JC69:** \(d=-3/4\ln(1-4p/3)\).
- **K2P:** \(d=-1/2\ln(1-2P-Q)-1/4\ln(1-2Q)\), with \(P\) and \(Q\) the transition and transversion proportions.

Corrected distances estimate substitutions per comparable site under the model assumptions. Calculations report an error for no comparable sites or undefined logarithms (saturation); they never silently substitute a finite result. Sequences must have equal aligned length and unique identifiers. The application does **not** perform alignment, phylogenetic tree inference, bootstrap, model selection, or recombination detection.

## Python command-line interface

The scientific calculation itself uses only the Python standard library (Python 3.10 or later).

~~~bash
python phylo_dist.py matrix --input aligned.fasta --output distances.csv --model jc69
python phylo_dist.py matrix --input aligned.fasta --output distances.phy --model k2p --format phylip
~~~

Available models: `p`, `jc69`, `k2p`. Formats: `csv`, `tsv`, `phylip`. Strict PHYLIP output requires identifiers of ten or fewer characters without spaces; CSV accommodates longer names.

The pre-existing term-lookup functionality is retained:

~~~bash
python phylo_dist.py single jc69
python phylo_dist.py batch --input sample.csv --output results.csv
~~~

These legacy commands perform terminology matching, **not** sequence-distance calculation.

## Optional server and API

~~~bash
python -m pip install -r requirements.txt
python cli.py serve --host 127.0.0.1 --port 8000
~~~

The standalone browser interface is served at <http://127.0.0.1:8000/> and OpenAPI documentation at <http://127.0.0.1:8000/docs>.

~~~bash
curl -X POST http://127.0.0.1:8000/api/matrix \
  -H 'Content-Type: application/json' \
  -d '{"model":"p","fasta":">Taxon_A\nACGT\n>Taxon_B\nATGT\n"}'
~~~

The `POST /api/matrix` response includes `taxa`, `model` and a square `distances` matrix. The backend retains legacy `/api/audit`, `/api/chat`, `/api/audit/logs`, `/health` and `/metrics` endpoints and the `cli.py audit/chat/batch` commands. These supervisor routines implement **generic threshold simulations**, not phylogenetic inference, clinical decision support, or validated scientific interpretations. The chat provider is an offline mock.

## Tests

~~~bash
python -m pip install -r requirements.txt pytest httpx
pytest -q
node --test web/app.test.mjs
node --check web/app.mjs
~~~

CI runs the Python tests on versions 3.10–3.12, exercises the browser calculations using Node, and builds the container.

## Local container

~~~bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
~~~

Compose binds only `127.0.0.1:8000`. Do not expose the generic audit endpoints on public networks without access controls.

## Privacy, security and limitations

Browser FASTA analysis and exports stay on the user's device. The optional REST API **does** receive requests at the configured server; it does not store submitted FASTA sequences on disk. Server infrastructure and network logging are outside the application's control.

The legacy supervisor uses limited regex-based identifier checks and an in-memory HMAC-SHA256 chain. Regexes cannot guarantee PHI detection or de-identification. Set a strong private `AUDIT_SECRET_KEY` on the backend. The audit chain is not persistent or a substitute for a regulated audit system. No HIPAA compliance is claimed.

## Technologies and license

Python 3.10+ with a standard-library calculation core; optional FastAPI, Pydantic and Uvicorn server; HTML, CSS and dependency-free ES-module JavaScript in the browser. MIT license; see [LICENSE](LICENSE).
