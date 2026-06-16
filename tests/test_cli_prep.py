from pathlib import Path

from nexus.cli.prep import load_config_overrides
from nexus.config import GlobalConfig


def test_load_config_overrides_applies_cli_flags(tmp_path, monkeypatch):
    # Ensure load_global_config returns a benign global config
    my_global = GlobalConfig()
    my_global.path.scratch_dir = tmp_path / "scratch"

    import nexus.config as nc
    monkeypatch.setattr(nc, "load_global_config", lambda path=None: my_global)

    cfg = load_config_overrides(
        None,
        {"input": tmp_path / "input.sdf", "output_dir": tmp_path / "out", "suffix": None},
        "lig",
        {"n_jobs": 4},
    )

    assert cfg.common.input == Path(tmp_path / "input.sdf")
    assert cfg.common.output_dir == Path(tmp_path / "out")
    assert cfg.lig.n_jobs == 4
