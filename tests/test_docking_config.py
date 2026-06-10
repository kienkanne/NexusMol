from pathlib import Path

import pytest

from nexus.dock.dock_config import load_dock_config


def write_docking_config(path, tmp_path, receptor_source, ligand_source, receptor_block):
    path.write_text(
        "libs:\n"
        "  chimerax: chimerax\n"
        "  chimera: chimera\n"
        "  dock_home: dock6\n"
        "common:\n"
        "  job_name: demo\n"
        f"  working_dir: {tmp_path / 'work'}\n"
        f"  results_dir: {tmp_path / 'results'}\n"
        "  n_jobs: 2\n"
        "  max_poses: 3\n"
        f"{receptor_block}"
        "ligands:\n"
        f"  source: {ligand_source}\n"
        "  suffix: _prepared.pdbqt\n"
        "vina:\n"
        "  exhaustiveness: 8\n"
        "  num_modes: 2\n"
    )


def test_load_dock_config_resolves_selection_receptor_bundles(tmp_path):
    receptors = tmp_path / "receptors"
    ligands = tmp_path / "ligands"
    receptors.mkdir()
    ligands.mkdir()
    receptor = receptors / "rec1.pdb"
    ligand = ligands / "lig1_prepared.pdbqt"
    receptor.write_text("protein")
    ligand.write_text("ligand")

    config_path = tmp_path / "dock.yaml"
    write_docking_config(
        config_path,
        tmp_path,
        receptors,
        ligands,
        "receptors:\n"
        f"  source: {receptors}\n"
        "  suffix: .pdb\n"
        "  pocket_option: selection\n"
        "  selection: /A:41,145\n",
    )

    cfg = load_dock_config(config_path)

    assert cfg.common.working_dir == tmp_path / "work" / "demo"
    assert cfg.common.results_dir == tmp_path / "results" / "demo"
    assert cfg.receptors.source == [receptor]
    assert cfg.ligands.source == [ligand]
    assert cfg.vina.exhaustiveness == 8
    assert cfg.receptors.bundles[0].receptor == receptor
    assert cfg.receptors.bundles[0].selection_string == "/A:41,145"


def test_load_dock_config_resolves_reference_pocket(tmp_path):
    receptor = tmp_path / "6W63_protein.pdb"
    reference = tmp_path / "6W63_pocket.pdb"
    ligand = tmp_path / "lig_prepared.pdbqt"
    receptor.write_text("protein")
    reference.write_text("pocket")
    ligand.write_text("ligand")

    config_path = tmp_path / "dock_reference.yaml"
    write_docking_config(
        config_path,
        tmp_path,
        receptor,
        ligand,
        "receptors:\n"
        f"  source: {receptor}\n"
        "  suffix: .pdb\n"
        "  pocket_option: reference\n"
        f"  reference: {reference}\n",
    )

    cfg = load_dock_config(config_path)

    assert cfg.receptors.reference == [reference]
    assert cfg.receptors.bundles[0].reference_path == reference
    assert cfg.receptors.bundles[0].selection_string is None


def test_load_dock_config_rejects_missing_selection(tmp_path):
    receptor = tmp_path / "rec.pdb"
    ligand = tmp_path / "lig_prepared.pdbqt"
    receptor.write_text("protein")
    ligand.write_text("ligand")
    config_path = tmp_path / "bad.yaml"
    write_docking_config(
        config_path,
        tmp_path,
        receptor,
        ligand,
        "receptors:\n"
        f"  source: {receptor}\n"
        "  suffix: .pdb\n"
        "  pocket_option: selection\n",
    )

    with pytest.raises(ValueError, match="no selection"):
        load_dock_config(config_path)
