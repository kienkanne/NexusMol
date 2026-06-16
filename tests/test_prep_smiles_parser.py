from pathlib import Path

import pytest


def test_sanitize_and_parse_csv_success(tmp_path):
    mod = __import__("nexus.prep.lig._parallel_rdkit_gen3d", fromlist=["*"])
    _sanitize_name = mod._sanitize_name
    _parse_ligands_csv = mod._parse_ligands_csv

    assert _sanitize_name(" acetyl-1 ") == "acetyl-1"
    assert _sanitize_name("A B") == "A_B"

    csv_path = tmp_path / "ligs.csv"
    csv_path.write_text("smiles,name\nCCO,ethanol\nCCC,propane\n")

    smiles, names = _parse_ligands_csv(csv_path)
    assert smiles == ["CCO", "CCC"]
    assert names == ["ethanol", "propane"]


def test_parse_csv_bad_header(tmp_path):
    mod = __import__("nexus.prep.lig._parallel_rdkit_gen3d", fromlist=["*"])
    _parse_ligands_csv = mod._parse_ligands_csv

    p = tmp_path / "bad.csv"
    p.write_text("smiles,wrong\nCCO,ethanol\n")

    with pytest.raises(ValueError, match="header"):
        _parse_ligands_csv(p)


def test_parse_csv_missing_values_and_duplicates(tmp_path):
    mod = __import__("nexus.prep.lig._parallel_rdkit_gen3d", fromlist=["*"])
    _parse_ligands_csv = mod._parse_ligands_csv

    p = tmp_path / "missing.csv"
    p.write_text("smiles,name\n,ethanol\n")
    with pytest.raises(ValueError):
        _parse_ligands_csv(p)

    p2 = tmp_path / "dup.csv"
    p2.write_text("smiles,name\nCCO,ethanol\nCCO,ethanol2\n")
    with pytest.raises(ValueError):
        _parse_ligands_csv(p2)

    # Duplicate names after sanitization
    p3 = tmp_path / "dup_name.csv"
    p3.write_text("smiles,name\nCCO,Name A\nCCC,Name A\n")
    with pytest.raises(ValueError):
        _parse_ligands_csv(p3)
