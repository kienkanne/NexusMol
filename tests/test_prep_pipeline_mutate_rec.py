from pathlib import Path
import types
import sys

import pytest

from nexus.prep.prep_config import PrepConfig


def test_mutate_pipeline_splits_mutations_and_calls_chimerax(monkeypatch, tmp_path):
    cfg = PrepConfig()
    cfg.mutate.mutations = ["A:10-GLY", "B:2-ALA"]
    cfg.common.input = tmp_path / "in"

    # monkeypatch the `extract_files` name imported into the mutate pipeline module
    import nexus.prep.mutate.mutate_pipeline as mp
    monkeypatch.setattr(mp, "extract_files", lambda inp, pats: [tmp_path / "rec.pdb"])

    called = {}

    def fake_chimerax(cfg_passed):
        called['ok'] = True

    # Mutate pipeline imported chimerax_mutate into its namespace; patch there
    import nexus.prep.mutate.mutate_pipeline as mp
    monkeypatch.setattr(mp, "chimerax_mutate", fake_chimerax)

    from nexus.prep.mutate.mutate_pipeline import MutatePipeline

    MutatePipeline(cfg=cfg)._run()

    assert isinstance(cfg.mutate.mutations, list)
    assert called.get('ok') is True


def test_mutate_and_rec_pipeline_raise_on_no_input(monkeypatch):
    cfg = PrepConfig()
    cfg.common.input = Path("/no/such/path")

    # make extract_files (as referenced by the pipeline modules) return empty list
    import nexus.prep.mutate.mutate_pipeline as mp
    import nexus.prep.rec.rec_pipeline as rp
    monkeypatch.setattr(mp, "extract_files", lambda inp, pats: [])
    monkeypatch.setattr(rp, "extract_files", lambda inp, pats: [])

    from nexus.prep.mutate.mutate_pipeline import MutatePipeline
    from nexus.prep.rec.rec_pipeline import RecPipeline

    with pytest.raises(ValueError):
        MutatePipeline(cfg=cfg)._run()

    with pytest.raises(ValueError):
        RecPipeline(cfg=cfg)._run()
