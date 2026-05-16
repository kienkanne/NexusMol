from compdd.dock6._dock6_prep_rec import _dock6_prep_rec
from compdd.dock6._dock6_docking import _dock6_docking
from compdd.docking_utils._write_summary_csv import _write_summary_csv
from compdd.config import load_config
from pathlib import Path
cfg = load_config("/home/kbui/Comp_DD/tests/test_config.yaml")

selected_spheres = _dock6_prep_rec(cfg)

out_files, lig_names = _dock6_docking(cfg, [Path("/home/kbui/Comp_DD/tests/data/mol16_prepped.mol2"),
                                Path("/home/kbui/Comp_DD/tests/data/mol17_prepped.mol2")])

_write_summary_csv(cfg, out_files, lig_names, program="dock6")
