from pydantic import BaseModel
from nexus.md.md_config import MDConfig

from nexus.md.amber._minimize import minimize
from nexus.md.amber._heat import heat
from nexus.md.amber._equilibrate import equilibrate
from nexus.md.amber._produce import produce

class AmberPipeline(BaseModel):
    mcfg: MDConfig

    def _run(self):
        ### Do checks to prmtop and ncrst if exists
        prmtop = self.mcfg.common.prmtop
        inpcrd = self.mcfg.common.inpcrd

        last_min_ncrst = minimize(self.mcfg, prmtop, inpcrd)
        last_heat_ncrst = heat(self.mcfg, prmtop, last_min_ncrst)
        last_eq_ncrst = equilibrate(self.mcfg, prmtop, last_heat_ncrst)
        
        ### TODO:
        # Returns trajectory file and out file for each seed to be copied to results_dir
        # Add production chunks, then combine at the end
        # Trajectory file should be removed from artifacts as it's very heavy
        produce(self.mcfg, prmtop, last_eq_ncrst)
        print (last_eq_ncrst)


### test
from nexus.md.md_config import MDConfig, load_md_config


mcfg = load_md_config("/localscratch/kbui/NexusMol/build/sample_configs/amber_md.yaml")

AmberPipeline(mcfg=mcfg)._run()