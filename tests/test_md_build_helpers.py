import os
from types import SimpleNamespace
import sys
import types
from pathlib import Path

import pytest


def test_run_pdb4amber_constructs_path_and_uses_shell(monkeypatch, tmp_path):
    # Create a dummy cfg object
    receptor = tmp_path / "rec.pdb"
    receptor.write_text("")
    global_ns = SimpleNamespace(path=SimpleNamespace(scratch_dir=tmp_path))
    cfg = SimpleNamespace(common=SimpleNamespace(receptor=receptor), _global=global_ns)

    # Patch shell in module
    import nexus.md.build._pdb4amber as mod

    class DummyCtx:
        def __init__(self, cmd, title=None):
            self.cmd = cmd

        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(mod, "shell", DummyCtx)

    out = mod._run_pdb4amber(cfg)
    assert out == tmp_path / f"{receptor.stem}_renamed.pdb"


def test_mmpbsa_pipeline_requires_amberhome(tmp_path, monkeypatch):
    # Ensure AMBERHOME not set
    monkeypatch.delenv("AMBERHOME", raising=False)

    from nexus.md.mmpbsa.mmpbsa_config import MMPBSAConfig
    from nexus.md.mmpbsa.mmpbsa_pipeline import MMPBSAPipeline

    # minimal valid config: create placeholder prmtop and trajin
    prmtop = tmp_path / "sys.prmtop"
    prmtop.write_text("")
    trajin = tmp_path / "traj.nc"
    trajin.write_text("")

    cfg = MMPBSAConfig(common={"prmtop": prmtop, "trajin": trajin, "receptor_mask": ":A"})
    cfg._global = SimpleNamespace(path=SimpleNamespace(scratch_dir=tmp_path))

    with pytest.raises(RuntimeError):
        MMPBSAPipeline(cfg=cfg)._run()
