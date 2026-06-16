import yaml
from pathlib import Path

import pytest

from nexus.config import (
    get_global_config_path,
    save_global_config,
    load_global_config,
    write_default_config,
    validate_global_config,
    GlobalConfig,
    clear_scratch,
)


def test_get_global_config_path_is_yaml():
    p = get_global_config_path()
    assert isinstance(p, Path)
    assert p.name == "config.yaml"


def test_save_and_load_global_config(tmp_path):
    cfg = GlobalConfig()
    cfg.software.chimerax = tmp_path / "bin" / "chim"

    out = save_global_config(cfg, path=tmp_path / "cfg.yaml", force=True)
    assert out.exists()

    loaded = load_global_config(path=out)
    assert isinstance(loaded, GlobalConfig)
    assert loaded.software.chimerax == cfg.software.chimerax


def test_save_global_config_no_overwrite(tmp_path):
    p = tmp_path / "cfg2.yaml"
    p.write_text("original")
    cfg = GlobalConfig()

    out = save_global_config(cfg, path=p, force=False)
    assert out == p
    assert p.read_text() == "original"


def test_load_global_config_missing_returns_default(tmp_path):
    p = tmp_path / "does_not_exist.yaml"
    loaded = load_global_config(path=p)
    assert isinstance(loaded, GlobalConfig)


def test_load_global_config_invalid_yaml_returns_default(tmp_path):
    p = tmp_path / "invalid.yaml"
    p.write_text("[]")
    loaded = load_global_config(path=p)
    assert isinstance(loaded, GlobalConfig)


def test_write_default_config_creates_file(tmp_path):
    p = tmp_path / "default.yaml"
    out = write_default_config(path=p, force=True)
    assert out.exists()
    assert p.exists()


def test_validate_global_config_paths(tmp_path):
    exists = tmp_path / "exists.bin"
    exists.write_text("ok")
    missing = tmp_path / "missing.bin"
    cfg_path = tmp_path / "config.yaml"
    data = {"software": {"chimerax": str(exists), "dock6": str(missing)}, "path": {"scratch_dir": None}}

    with open(cfg_path, "w") as fh:
        yaml.safe_dump(data, fh)

    results, has_missing = validate_global_config(cfg_path)
    assert results["software.chimerax"] == "OK"
    assert results["software.dock6"] == "Missing path"
    assert has_missing is True


def test_clear_scratch_removes_dir(tmp_path):
    holder = type("Holder", (), {})()
    holder._global = GlobalConfig()
    holder._global.path.clear = True
    holder._global.path.scratch_dir = tmp_path / "scratch"
    holder._global.path.scratch_dir.mkdir()
    assert holder._global.path.scratch_dir.exists()

    clear_scratch(holder)
    assert not holder._global.path.scratch_dir.exists()
