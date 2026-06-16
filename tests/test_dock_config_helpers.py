from pathlib import Path
from types import SimpleNamespace
import pytest

from nexus.dock.dock_config import parse_selection_csv, match_references_to_receptors, _validate_and_normalize_receptors


def test_parse_selection_csv_and_errors(tmp_path):
    p = tmp_path / "sel.csv"
    p.write_text("A,/A:1\nB,/A:2\n")
    mapping = parse_selection_csv(p)
    assert mapping["A"] == "/A:1"

    bad = tmp_path / "bad.csv"
    bad.write_text("onlyonecolumn\n")
    with pytest.raises(ValueError):
        parse_selection_csv(bad)


def test_match_references_to_receptors_success_and_missing(tmp_path):
    r1 = tmp_path / "A_protein.pdb"
    r2 = tmp_path / "B_protein.pdb"
    r1.write_text("")
    r2.write_text("")

    ref1 = tmp_path / "A_pocket.pdb"
    ref2 = tmp_path / "B_pocket.pdb"
    ref1.write_text("")
    ref2.write_text("")

    mapping = match_references_to_receptors([r1, r2], [ref1, ref2], "_pocket.pdb")
    assert mapping[r1] == ref1
    assert mapping[r2] == ref2

    # Missing reference should raise
    with pytest.raises(FileNotFoundError):
        match_references_to_receptors([r1], [ref2], "_pocket.pdb")


def test_validate_and_normalize_receptors_selection_and_reference(tmp_path):
    # Prepare receptors list
    r1 = tmp_path / "A_protein.pdb"
    r2 = tmp_path / "B_protein.pdb"
    r1.write_text("")
    r2.write_text("")

    # Selection global
    receptors_ns = SimpleNamespace(source=[r1, r2], pocket_option="selection", selection="/A:1", reference=None, reference_suffix="_pocket.pdb")
    cfg = SimpleNamespace(receptors=receptors_ns)
    bundles = _validate_and_normalize_receptors(cfg)
    assert len(bundles) == 2
    assert all(b.selection_string == "/A:1" for b in bundles)

    # Reference mapping
    ref1 = tmp_path / "A_pocket.pdb"
    ref2 = tmp_path / "B_pocket.pdb"
    ref1.write_text("")
    ref2.write_text("")
    receptors_ns2 = SimpleNamespace(source=[r1, r2], pocket_option="reference", reference=[ref1, ref2], reference_suffix="_pocket.pdb")
    cfg2 = SimpleNamespace(receptors=receptors_ns2)
    bundles2 = _validate_and_normalize_receptors(cfg2)
    assert len(bundles2) == 2
    assert bundles2[0].reference_path in [ref1, ref2]
