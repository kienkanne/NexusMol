from compdd.configs.docking_config import load_docking_config


def test_load_docking_config_keeps_ligands_out_of_common(tmp_path):
    config_yaml = tmp_path / "docking.yaml"
    config_yaml.write_text(
        "libs:\n"
        "  chimerax: chimerax\n"
        "  chimera: chimera\n"
        "  mgltools: mgltools\n"
        "  dock_home: dock6\n"
        "  obabel: obabel\n"
        "  parallel: parallel\n"
        "  vina: vina\n"
        "common:\n"
        "  project_name: demo\n"
        f"  working_dir: {tmp_path / 'work'}\n"
        f"  results_dir: {tmp_path / 'results'}\n"
        f"  receptor: {tmp_path / 'rec.pdb'}\n"
        "  prepared_suffix: ready\n"
        "vina: {}\n"
        "dock6: {}\n"
    )

    cfg = load_docking_config(config_yaml)

    assert cfg.common.prepared_suffix == "ready"
    assert cfg.common.working_dir == tmp_path / "work" / "demo"
    assert cfg.common.results_dir == tmp_path / "results" / "demo"
    assert not hasattr(cfg.common, "ligands_csv")


def test_load_docking_config_reference_option(tmp_path):
    config_yaml = tmp_path / "docking_reference.yaml"
    reference = tmp_path / "pocket.pdb"
    config_yaml.write_text(
        "libs:\n"
        "  chimerax: chimerax\n"
        "  chimera: chimera\n"
        "  mgltools: mgltools\n"
        "  dock_home: dock6\n"
        "  obabel: obabel\n"
        "  parallel: parallel\n"
        "  vina: vina\n"
        "common:\n"
        "  project_name: demo\n"
        f"  working_dir: {tmp_path / 'work'}\n"
        f"  results_dir: {tmp_path / 'results'}\n"
        f"  receptor: {tmp_path / 'rec.pdb'}\n"
        "  pocket_option: reference\n"
        f"  reference: {reference}\n"
        "vina: {}\n"
        "dock6: {}\n"
    )

    cfg = load_docking_config(config_yaml)

    assert cfg.common.pocket_option == "reference"
    assert cfg.common.reference == reference
