from pathlib import Path
from types import SimpleNamespace

from compdd.vina._vina_docking import _build_vina_docking_commands
from compdd.vina._vina_prep_rec import VinaReceptorBundle


def test_vina_docking_builds_commands_with_receptor_bundle():
    cfg = SimpleNamespace(
        libs=SimpleNamespace(vina="vina"),
        common=SimpleNamespace(prepared_suffix="prepped"),
    )
    receptor = VinaReceptorBundle(
        receptor=Path("rec1_prepped.pdbqt"),
        vina_config=Path("rec1_config.txt"),
        name="rec1",
    )
    ligand = Path("ligA_prepped.pdbqt")

    out_files, cmds = _build_vina_docking_commands(cfg, [(receptor, ligand)])

    assert out_files == ["rec1_ligA_scored.pdbqt"]
    assert cmds[0][0] == "vina"
    assert "--receptor" in cmds[0]
    assert str(receptor.vina_config) in cmds[0]
    assert str(ligand) in cmds[0]
