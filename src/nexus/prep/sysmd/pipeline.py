from pydantic import BaseModel
from pathlib import Path
import os
from nexus.prep.prep_config import PrepConfig
from nexus.prep.sysmd._pdb4amber import _run_pdb4amber
from nexus.prep.sysmd._select_pose import _select_pose
from nexus.prep.sysmd._process_ligand import _process_ligand
from nexus.prep.sysmd._tleap import run_tleap


class SysmdPipeline(BaseModel):
    pcfg: PrepConfig

    def _run(self):
        AMBERHOME = os.environ.get("AMBERHOME")
        if not AMBERHOME:
            raise RuntimeError("AMBERHOME environment variable not set")
        
        if self.pcfg.common.working_dir is None:
            self.pcfg.common.working_dir = Path.cwd()
    
        self.pcfg.common.working_dir= self.pcfg.common.working_dir / self.pcfg.sysmd.system_name
        self.pcfg.common.output_dir = self.pcfg.common.output_dir / self.pcfg.sysmd.system_name

        self.pcfg.common.working_dir.mkdir(parents=True, exist_ok=True)
        self.pcfg.common.output_dir.mkdir(parents=True, exist_ok=True)
        
        receptor_named = _run_pdb4amber(self.pcfg)
        if self.pcfg.sysmd.ligand is None:
            ligand_charged = ligand_frcmod = None
        else:
            ligand_pose = _select_pose(self.pcfg)
            ligand_charged, ligand_frcmod = _process_ligand(self.pcfg, ligand_pose)
        run_tleap(self.pcfg, receptor_named, ligand_charged, ligand_frcmod)
