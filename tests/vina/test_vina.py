from compdd.vina._vina_prep_rec import _vina_prep_rec
from compdd.vina._vina_docking import _vina_docking
from compdd.docking_utils._write_summary_csv import _write_summary_csv
from compdd.config import load_config
from pathlib import Path
cfg = load_config("/home/kbui/Comp_DD/tests/test_config.yaml")

prepped_rec, vina_config = _vina_prep_rec(cfg)

out_files, lig_names = _vina_docking(cfg, [Path("/home/kbui/Comp_DD/tests/data/mol16_prepped.pdbqt"),
                                Path("/home/kbui/Comp_DD/tests/data/mol17_prepped.pdbqt")],
                                prepped_rec,
                                vina_config)

_write_summary_csv(cfg, out_files, lig_names, program="vina")


