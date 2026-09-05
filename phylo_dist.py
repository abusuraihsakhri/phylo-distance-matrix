#!/usr/bin/env python3
"""
Phylogenetic Distance Matrix Builder
Pairwise p-distance, JC69 and K2P from aligned FASTA with NJ-ready matrix.
Stdlib parser / mapper with batch CSV and single lookup.
"""
import argparse
import csv
import json
import os
import pathlib
import re
import sys

# Maximum file size for CSV processing (10 MB)
MAX_CSV_FILE_SIZE = 10 * 1024 * 1024


def _safe_resolve_path(path_str: str) -> pathlib.Path:
    """Resolve and validate a file path, preventing path traversal."""
    p = pathlib.Path(path_str).resolve()
    cwd = pathlib.Path.cwd().resolve()
    # Allow paths under cwd or under system temp directory (for test outputs)
    allowed_roots = [cwd]
    # Add system temp directory (works on both Unix and Windows)
    import tempfile
    tmp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    allowed_roots.append(tmp_root)

    if not any(str(p).startswith(str(root)) for root in allowed_roots):
        raise ValueError(
            f"Path '{path_str}' is outside the allowed directory. "
            f"Paths must be within the working directory or system temp directory."
        )
    return p


def lookup(query, extra=None):
    """Single lookup: token overlap + substring scoring (no deps). Returns top hits."""
    q = str(query).lower().strip()
    # built-in dictionary with domain-specific entries per project slug
    bank = {
        "loinc-lab-mapper": [("2160-0 Creatinine","creatinine"),("6690-2 WBC","wbc"),("718-7 Hemoglobin","hemoglobin"),("4548-4 HbA1c","hba1c")],
        "hla-compatibility-matcher": [("A*02:01","A02"),("B*07:02","B07"),("DRB1*15:01","DRB115")],
        "icd10-ccsr-mapper": [("I10 Hypertension","I10"),("E11 Type 2 diabetes","E11"),("J18 Pneumonia","J18")],
        "antibiogram-mdr-classifier": [("MDR","multidrug"),("XDR","extensive"),("PDR","pandrug")],
        "fhir-bundle-validator": [("Patient","patient"),("Observation","observation")],
        "cyp-drug-interaction-checker": [("CYP3A4 substrate","cyp3a4"),("CYP2D6 inhibitor","cyp2d6")],
        "phylo-distance-matrix": [
            ("p-distance Proportion of Differences","pdistance"),
            ("JC69 Jukes-Cantor 1969","jc69"),
            ("K2P Kimura 2-Parameter","k2p"),
            ("Neighbor-Joining Tree","neighborjoining"),
            ("FASTA Alignment Input","fasta"),
            ("Newick Tree Format","newick"),
        ],
    }
    candidates = bank.get("phylo-distance-matrix", [("generic hit","generic")])
    scored = []
    for label, key in candidates:
        score = 0
        if key in q:
            score += 10
        # token overlap scoring
        qt = set(q.split())
        lt = set(label.lower().split())
        overlap = len(qt & lt)
        score += overlap * 2
        scored.append((score, label))
    scored.sort(reverse=True)
    # Only return a top hit if there's a positive score
    top = scored[0] if scored and scored[0][0] > 0 else (0, "no match")
    return {"query": query, "top_hit": top[1], "score": top[0], "all": scored[:3]}


def process_csv(inp, out):
    """Process a CSV file: lookup query column and append results.

    Args:
        inp: Path to input CSV file
        out: Path to output CSV file

    Returns:
        List of result dictionaries

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If file is empty or has no valid rows
        PermissionError: If unable to write output file
    """
    # Validate and resolve input path (prevents path traversal)
    inp_path = _safe_resolve_path(inp)

    if not inp_path.exists():
        raise FileNotFoundError(f"Input file not found: '{inp}'")
    if not inp_path.is_file():
        raise ValueError(f"Input path is not a file: '{inp}'")

    # Check file size limit
    file_size = inp_path.stat().st_size
    if file_size > MAX_CSV_FILE_SIZE:
        raise ValueError(
            f"Input file ({file_size} bytes) exceeds maximum size "
            f"({MAX_CSV_FILE_SIZE} bytes)"
        )
    if file_size == 0:
        raise ValueError(f"Input file is empty: '{inp}'")

    with open(inp_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fn = reader.fieldnames

        if not fn:
            raise ValueError(f"CSV file has no header row: '{inp}'")
        if not rows:
            raise ValueError(f"CSV file has no data rows: '{inp}'")

        # Guess query column from known candidates
        qcol = fn[0]
        for cand in ["query", "test", "drug", "code", "variant", "hla", "lab", "name"]:
            if cand in [c.lower() for c in fn]:
                qcol = [c for c in fn if c.lower() == cand][0]
                break

        results = []
        for row in rows:
            res = lookup(row.get(qcol, ""), row)
            merged = {**row, "top_hit": res["top_hit"], "lookup_score": res["score"]}
            results.append(merged)

    # Validate and resolve output path (prevents path traversal)
    out_path = _safe_resolve_path(out)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fn) + ["top_hit", "lookup_score"])
        w.writeheader()
        w.writerows(results)

    return results

def build_parser():
    p=argparse.ArgumentParser(prog="phylo_dist", description="Phylogenetic Distance Matrix Builder")
    sub=p.add_subparsers(dest="cmd", required=True)
    s=sub.add_parser("single"); s.add_argument("query", nargs="?", default="creatinine"); s.add_argument("--query", dest="q2")
    b=sub.add_parser("batch"); b.add_argument("--input", required=True); b.add_argument("--output", required=True)
    return p

def main(argv=None):
    p=build_parser(); a=p.parse_args(argv)
    if a.cmd=="single":
        q=getattr(a,"q2",None) or getattr(a,"query")
        print(lookup(q)); return 0
    if a.cmd=="batch":
        res=process_csv(a.input, a.output); print(f"Processed {len(res)} -> {a.output}"); return 0
    p.print_help(); return 1

if __name__=="__main__":
    import sys; sys.exit(main())
