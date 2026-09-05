import os
import pathlib
import tempfile

import pytest

import phylo_dist as m


def test_lookup_returns_expected_fields():
    r = m.lookup("jc69")
    assert "top_hit" in r
    assert "score" in r
    assert "all" in r
    assert r["query"] == "jc69"


def test_lookup_domain_specific_entries():
    """Test that phylo-distance-matrix domain entries are in the bank."""
    r = m.lookup("pdistance")
    assert r["top_hit"] == "p-distance Proportion of Differences"
    assert r["score"] > 0


def test_lookup_k2p_entry():
    r = m.lookup("k2p")
    assert r["top_hit"] == "K2P Kimura 2-Parameter"
    assert r["score"] > 0


def test_lookup_neighbor_joining_entry():
    r = m.lookup("neighborjoining")
    assert r["top_hit"] == "Neighbor-Joining Tree"
    assert r["score"] > 0


def test_lookup_fasta_entry():
    r = m.lookup("fasta")
    assert r["top_hit"] == "FASTA Alignment Input"
    assert r["score"] > 0


def test_lookup_newick_entry():
    r = m.lookup("newick")
    assert r["top_hit"] == "Newick Tree Format"
    assert r["score"] > 0


def test_lookup_no_match():
    """Test lookup with gibberish input returns no match."""
    r = m.lookup("xyzzyqqq12345nomatch")
    assert r["top_hit"] == "no match"
    assert r["score"] == 0


def test_lookup_empty_query():
    r = m.lookup("")
    assert "top_hit" in r
    assert "score" in r


def test_process_csv_success():
    """Test successful CSV processing."""
    pdir = pathlib.Path(__file__).parent
    out_path = str(pdir / "tmp_test_out.csv")
    try:
        rows = m.process_csv(str(pdir / "sample.csv"), out_path)
        assert len(rows) >= 1
        # Verify output columns were added
        for row in rows:
            assert "top_hit" in row
            assert "lookup_score" in row
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def test_process_csv_file_not_found():
    """Test that FileNotFoundError is raised for missing files."""
    pdir = pathlib.Path(__file__).parent
    with pytest.raises(FileNotFoundError):
        m.process_csv(str(pdir / "nonexistent_file.csv"), str(pdir / "tmp_out.csv"))


def test_process_csv_empty_file():
    """Test that ValueError is raised for empty files."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("")
        tmp_path = f.name
    try:
        with pytest.raises(ValueError, match="empty"):
            m.process_csv(tmp_path, "/tmp/out.csv")
    finally:
        os.remove(tmp_path)


def test_process_csv_no_header():
    """Test that ValueError is raised for CSV with no header."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("\n")
        tmp_path = f.name
    try:
        with pytest.raises(ValueError, match="no header"):
            m.process_csv(tmp_path, "/tmp/out.csv")
    finally:
        os.remove(tmp_path)


def test_process_csv_path_traversal():
    """Test that path traversal attempts are blocked."""
    with pytest.raises(ValueError, match="outside the allowed directory"):
        m.process_csv("../../../etc/passwd", "/tmp/out.csv")


def test_safe_resolve_path_within_cwd():
    """Test that paths within cwd are allowed."""
    # A relative path like "sample.csv" should resolve within cwd
    result = m._safe_resolve_path("sample.csv")
    assert isinstance(result, pathlib.Path)


def test_safe_resolve_path_traversal():
    """Test that path traversal attempts raise ValueError."""
    with pytest.raises(ValueError):
        m._safe_resolve_path("../../etc/passwd")
