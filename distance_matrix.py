"""Pairwise nucleotide distances from an already aligned FASTA file.

Ambiguous bases and gaps are omitted separately for each sequence pair.
No alignment, tree inference, or model fitting is performed.
"""
import csv
import io
import math
import re

DNA = set("ACGT")
ALLOWED = set("ACGTRYSWKMBDHVN-.?")
MODELS = ("p", "jc69", "k2p")
FORMATS = ("csv", "tsv", "phylip")


def parse_fasta(text):
    """Return ordered (identifier, sequence) records from aligned DNA FASTA."""
    if not isinstance(text, str):
        raise ValueError("FASTA input must be text")
    records = []
    label, chunks = None, []
    for line_number, raw in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if label is not None:
                records.append((label, "".join(chunks)))
            label = line[1:].strip()
            if not label:
                raise ValueError(f"Empty FASTA identifier on line {line_number}")
            chunks = []
        else:
            if label is None:
                raise ValueError(f"Sequence before first FASTA header on line {line_number}")
            sequence = line.upper()
            bad = set(sequence) - ALLOWED
            if bad:
                raise ValueError(f"Invalid DNA symbol {sorted(bad)[0]!r} on line {line_number}")
            chunks.append(sequence)
    if label is not None:
        records.append((label, "".join(chunks)))
    _validate_records(records)
    return records


def _validate_records(records):
    if len(records) < 2:
        raise ValueError("At least two FASTA sequences are required")
    labels = [name for name, _ in records]
    if len(set(labels)) != len(labels):
        raise ValueError("FASTA identifiers must be unique")
    widths = {len(seq) for _, seq in records}
    if len(widths) != 1 or not next(iter(widths)):
        raise ValueError("Sequences must be aligned, non-empty and equal in length")
    if any(set(seq) - ALLOWED for _, seq in records):
        raise ValueError("Invalid DNA symbol in a sequence")


def calculate_matrix(records, model="p"):
    """Calculate symmetric distances; raise on zero coverage or model saturation."""
    if model not in MODELS:
        raise ValueError("Model must be one of: " + ", ".join(MODELS))
    _validate_records(records)
    n = len(records)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            transitions = transversions = comparable = 0
            for a, b in zip(records[i][1], records[j][1]):
                if a not in DNA or b not in DNA:
                    continue
                comparable += 1
                if a != b:
                    if (a, b) in {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}:
                        transitions += 1
                    else:
                        transversions += 1
            pair = f"{records[i][0]!r} / {records[j][0]!r}"
            if not comparable:
                raise ValueError(f"No comparable A/C/G/T positions for {pair}")
            p = (transitions + transversions) / comparable
            if model == "p":
                value = p
            elif model == "jc69":
                term = 1 - 4 * p / 3
                if term <= 0:
                    raise ValueError(f"JC69 distance undefined (saturation) for {pair}")
                value = -0.75 * math.log(term)
            else:
                P, Q = transitions / comparable, transversions / comparable
                a, b = 1 - 2 * P - Q, 1 - 2 * Q
                if a <= 0 or b <= 0:
                    raise ValueError(f"K2P distance undefined (saturation) for {pair}")
                value = -0.5 * math.log(a) - 0.25 * math.log(b)
            matrix[i][j] = matrix[j][i] = value
    return matrix


def render_matrix(records, matrix, fmt="csv"):
    """Serialize a computed matrix as CSV, TSV, or strict PHYLIP sequential."""
    if fmt not in FORMATS:
        raise ValueError("Format must be one of: " + ", ".join(FORMATS))
    names = [name for name, _ in records]
    if len(matrix) != len(names) or any(len(row) != len(names) for row in matrix):
        raise ValueError("Matrix dimensions do not match FASTA records")
    if fmt == "phylip":
        if any(len(name) > 10 or any(c.isspace() for c in name) for name in names):
            raise ValueError("PHYLIP format requires unique identifiers of at most 10 non-space characters")
        return str(len(names)) + "\n" + "".join(
            name.ljust(10) + " " + " ".join(f"{value:.10f}" for value in row) + "\n"
            for name, row in zip(names, matrix)
        )
    out = io.StringIO(newline="")
    writer = csv.writer(out, delimiter="," if fmt == "csv" else "\t", lineterminator="\n")
    # Prefix spreadsheet formula characters in downloadable labels only.
    safe = lambda name: "'" + name if name.lstrip().startswith(("=", "+", "-", "@")) else name
    writer.writerow(["taxon"] + [safe(name) for name in names])
    for name, row in zip(names, matrix):
        writer.writerow([safe(name)] + [f"{value:.10f}" for value in row])
    return out.getvalue()
