import sys
import types
from pathlib import Path

import pytest

from nexus.prep.prep_config import PrepConfig


def _inject_fake_module(name, attrs):
    import importlib
    try:
        mod = importlib.import_module(name)
    except ModuleNotFoundError:
        mod = types.ModuleType(name)
        sys.modules[name] = mod

    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def test_ligpipeline_csv_branch(tmp_path, monkeypatch):
    # Prepare config
    cfg = PrepConfig()
    csv_path = tmp_path / "ligs.csv"
    csv_path.write_text("smiles,name\nCCO,eth1\n")
    cfg.common.input = csv_path
    cfg.common.output_dir = tmp_path / "out"
    cfg.common.suffix = "_prepared.pdbqt"

    # Inject fake _smiles_to_mols and meeko charge modules
    def fake_smiles_to_mols(path, n_jobs):
        return ([object()], ["mol1"])

    def fake_parallel_meeko_charge(mols, outputs, n_jobs):
        return [outputs[0]]

    _inject_fake_module("nexus.prep.lig._smiles_to_mols", {"_smiles_to_mols": fake_smiles_to_mols})
    _inject_fake_module("nexus.prep.lig._meeko_charge", {"_parallel_meeko_charge": fake_parallel_meeko_charge})

    from nexus.prep.lig.lig_pipeline import LigPipeline

    lp = LigPipeline(cfg=cfg)
    out = lp._run()
    assert isinstance(out, list)
    assert out[0].name == "mol1_prepared.pdbqt" or str(out[0]).endswith("mol1_prepared.pdbqt")


def test_ligpipeline_sdf_branch_and_suffix_validation(tmp_path, monkeypatch):
    cfg = PrepConfig()
    # create a directory with sdfs
    inp = tmp_path / "indir"
    inp.mkdir()
    (inp / "a.sdf").write_text("data")
    cfg.common.input = inp
    cfg.common.output_dir = tmp_path / "out2"
    cfg.common.suffix = ".mol2"

    # Inject fake sdfs->mols and obabel charge
    def fake_sdfs_to_mols(sdfs, n_jobs):
        return ([object()], ["molA"])

    def fake_parallel_obabel_charge(mols, outputs, n_jobs):
        return [outputs[0]]

    _inject_fake_module("nexus.prep.lig._sdfs_to_mols", {"_sdfs_to_mols": fake_sdfs_to_mols})
    _inject_fake_module("nexus.prep.lig._obabel_charge", {"_parallel_obabel_charge": fake_parallel_obabel_charge})

    from nexus.prep.lig.lig_pipeline import LigPipeline

    lp = LigPipeline(cfg=cfg)
    out = lp._run()
    assert isinstance(out, list)

    # invalid suffix should raise
    cfg.common.suffix = "bad.suf"
    with pytest.raises(ValueError):
        LigPipeline(cfg=cfg)._run()
