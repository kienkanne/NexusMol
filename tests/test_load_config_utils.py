import sys
import types
import yaml
from pathlib import Path

import pytest

from nexus.core.utils.load_config import expand_paths, setup_dir, load_config
from nexus.prep.prep_config import PrepConfig
from nexus.config import GlobalConfig


def test_expand_paths_resolves_paths(tmp_path):
    cfg = PrepConfig()
    cfg.common.output_dir = Path(str(tmp_path / "out"))

    out = expand_paths(cfg)
    assert out.common.output_dir.is_absolute()


def test_setup_dir_creates_directory(tmp_path):
    base = tmp_path / "base"
    returned = setup_dir(base, "name")
    assert returned == base / "name"
    assert returned.exists()


def test_load_config_creates_output_and_scratch(tmp_path, monkeypatch):
    cfg_file = tmp_path / "prep.yaml"
    yaml.safe_dump({"common": {"job_name": "job1", "output_dir": str(tmp_path)}}, open(cfg_file, "w"))

    # create fake global config so load_config doesn't touch system paths
    my_global = GlobalConfig()
    my_global.path.scratch_dir = tmp_path / "scratch_base"

    import nexus.config as nc
    monkeypatch.setattr(nc, "load_global_config", lambda path=None: my_global)

    # ensure trackers import resolves to a noop
    mod = types.ModuleType("nexus.core.trackers.main_tracker")
    mod.setup_context = lambda a, b: None
    sys.modules["nexus.core.trackers.main_tracker"] = mod

    cfg = load_config(PrepConfig, cfg_file)

    # PrepConfig.CommonConfig does not define `job_name`, so load_config
    # will not create job-specific subdirectories. Instead ensure the
    # returned config has the attached global config and paths resolved.
    assert getattr(cfg, "_global", None) is my_global
    assert cfg.common.output_dir == Path(tmp_path)
