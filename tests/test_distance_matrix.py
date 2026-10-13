"""Scientific regression tests for the aligned-FASTA distance calculations."""
import csv
import io
import math

import pytest

from distance_matrix import parse_fasta, calculate_matrix, render_matrix
from phylo_dist import main


def test_multiline_fasta_and_identical_sequences():
    records = parse_fasta(">A\nacg\nT-\n>B\nACGT-\n")
    assert records == [("A", "ACGT-"), ("B", "ACGT-")]
    assert calculate_matrix(records) == [[0.0, 0.0], [0.0, 0.0]]


def test_models_against_analytic_values():
    records = parse_fasta(">A\nAAAAAAAAAA\n>B\nGAAAAAACAA\n")
    p = calculate_matrix(records, "p")[0][1]
    jc = calculate_matrix(records, "jc69")[0][1]
    k2p = calculate_matrix(records, "k2p")[0][1]
    assert p == pytest.approx(0.2)
    assert jc == pytest.approx(-0.75 * math.log(1 - 4 * 0.2 / 3))
    # One A->G transition plus one A->C transversion.
    assert k2p == pytest.approx(-0.5 * math.log(1 - 0.2 - 0.1) - 0.25 * math.log(1 - 0.2))


def test_pairwise_deletion_and_matrix_symmetry():
    records = parse_fasta(">A\nACGN-T\n>B\nATGATT\n>C\nACGANT\n")
    matrix = calculate_matrix(records, "p")
    assert matrix[0][1] == pytest.approx(1 / 4)
    assert matrix[0][2] == pytest.approx(0)
    assert matrix[1][2] == pytest.approx(1 / 5)
    assert all(matrix[i][j] == matrix[j][i] for i in range(3) for j in range(3))
    assert all(matrix[i][i] == 0 for i in range(3))


@pytest.mark.parametrize("content,message", [
    ("ACGT", "before first"),
    (">A\nACGT\n", "At least two"),
    (">A\nACG\n>A\nACG\n", "unique"),
    (">A\nACG\n>B\nACGT\n", "equal in length"),
    (">A\nACG\n>B\nAC@\n", "Invalid DNA"),
    (">A\n\n>B\n\n", "non-empty"),
    (">\nACGT\n>B\nACGT\n", "Empty FASTA"),
])
def test_fasta_validation(content, message):
    with pytest.raises(ValueError, match=message):
        parse_fasta(content)


def test_empty_overlap_and_saturation_fail_loudly():
    with pytest.raises(ValueError, match="No comparable"):
        calculate_matrix(parse_fasta(">A\nNN--\n>B\nAAAA\n"))
    data = parse_fasta(">A\nAAAA\n>B\nTTTT\n")
    assert calculate_matrix(data, "p")[0][1] == 1
    with pytest.raises(ValueError, match="JC69.*saturation"):
        calculate_matrix(data, "jc69")
    with pytest.raises(ValueError, match="K2P.*saturation"):
        calculate_matrix(data, "k2p")


def test_csv_export_quoting_and_formula_safety():
    records = parse_fasta('>="untrusted",name\nAAAA\n>Safe\nAAAA\n')
    out = render_matrix(records, calculate_matrix(records))
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[0][1].startswith("'=")
    assert rows[1][0] == rows[0][1]
    assert rows[1][2] == "0.0000000000"


def test_phylip_name_limit_and_tsv_output():
    records = parse_fasta(">Long Identifier\nAAAA\n>Short\nAAAA\n")
    with pytest.raises(ValueError, match="PHYLIP"):
        render_matrix(records, calculate_matrix(records), "phylip")
    assert "\t" in render_matrix(records, calculate_matrix(records), "tsv")
    short = parse_fasta(">A\nAAAA\n>B\nAAAA\n")
    assert render_matrix(short, calculate_matrix(short), "phylip").startswith("2\n")


def test_cli_computes_real_matrix(tmp_path):
    source = tmp_path / "alignment.fa"
    target = tmp_path / "distances.csv"
    source.write_text(">A\nACGT\n>B\nATGT\n", encoding="utf-8")
    assert main(["matrix", "--input", str(source), "--output", str(target), "--model", "p"]) == 0
    rows = list(csv.reader(io.StringIO(target.read_text())))
    assert rows[1][2] == "0.2500000000"
    assert rows[2][1] == "0.2500000000"
    with pytest.raises(ValueError, match="different"):
        main(["matrix", "--input", str(source), "--output", str(source)])
