from pydantic import BaseModel
import os
from nexus.config import clear_scratch
from nexus.md.build.build_config import BuildConfig
from nexus.md.build._pdb4amber import _run_pdb4amber
from nexus.md.build._select_pose import _select_pose
from nexus.md.build._process_ligand import _process_ligand
from nexus.md.build._tleap import run_tleap


class BuildPipeline(BaseModel):
    cfg: BuildConfig

    def _run(self):
        AMBERHOME = os.environ.get("AMBERHOME")
        if not AMBERHOME:
            raise RuntimeError("AMBERHOME environment variable not set")
        
        receptor_named = _run_pdb4amber(self.cfg)
        if self.cfg.ligand.ligand is None:
            ligand_charged = ligand_frcmod = None
        else:
            ligand_pose = _select_pose(self.cfg)
            ligand_charged, ligand_frcmod = _process_ligand(self.cfg, ligand_pose)
        run_tleap(self.cfg, receptor_named, ligand_charged, ligand_frcmod)

        clear_scratch(self.cfg)
