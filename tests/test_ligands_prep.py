import pytest

from compdd.configs.ligands_config import LigandsConfig, load_ligands_config
from compdd.ligands._ligands_common import _discover_prepared_ligands
from compdd.ligands.ligands_prep import _parse_ligands_csv


def test_parse_ligands_csv_preserves_smiles_name_pairs(tmp_path):
    csv_path = tmp_path / "ligands.csv"
    csv_path.write_text(
        "smiles,name\n"
        "Cc1ccc(C(C)C)cc1O,mol1\n"
        "C#CCOc1cc(C(C)C)ccc1C,mol2\n"
        "CC(=O)OC1=CC=CC=C1C(=O)O,aspirin\n"
    )

    assert _parse_ligands_csv(csv_path) == [
        ("Cc1ccc(C(C)C)cc1O", "mol1"),
        ("C#CCOc1cc(C(C)C)ccc1C", "mol2"),
        ("CC(=O)OC1=CC=CC=C1C(=O)O", "aspirin"),
    ]


def test_parse_ligands_csv_rejects_duplicate_sanitized_names(tmp_path):
    csv_path = tmp_path / "ligands.csv"
    csv_path.write_text("smiles,name\nCC,lig 1\nCCC,lig_1\n")

    with pytest.raises(ValueError, match="Duplicate ligand name"):
        _parse_ligands_csv(csv_path)


def test_load_ligands_config_attaches_program(tmp_path):
    csv_path = tmp_path / "ligands.csv"
    csv_path.write_text("smiles,name\nCC,ethane\n")
    ligands_yaml = tmp_path / "ligands.yaml"
    ligands_yaml.write_text(
        "source: smiles\n"
        "prepared_suffix: ready\n"
        f"smiles_csv: {csv_path}\n"
        f"results_dir: {tmp_path / 'prepared'}\n"
        "prepare_tool: meeko\n"
    )

    cfg = load_ligands_config(ligands_yaml, program="vina")

    assert cfg.program == "vina"
    assert cfg.prepared_suffix == "ready"
    assert cfg.prepare_tool == "meeko"


def test_discover_prepared_ligands_uses_program_extension(tmp_path):
    (tmp_path / "mol1_ready.pdbqt").write_text("vina")
    (tmp_path / "mol2_ready.pdbqt").write_text("vina")
    (tmp_path / "mol3_ready.mol2").write_text("dock6")

    cfg = LigandsConfig(
        source="files",
        prepared_suffix="ready",
        ligands_dir=tmp_path,
        program="vina",
    )

    assert [path.name for path in _discover_prepared_ligands(cfg)] == [
        "mol1_ready.pdbqt",
        "mol2_ready.pdbqt",
    ]
