from functools import partial
from pathlib import Path

from nexus.core.executors.python_parallel import python_parallel
from nexus.core.executors.gnu_parallel import gnu_parallel

from nexus.prep.ligdock._parse_csv import _parse_ligands_csv
from nexus.prep.prep_config import PrepConfig

def ligands_prep(pcfg: PrepConfig):
    #@main_tracker(pcfg, "Prepare ligands")
    def _run():
        """if pcfg.ligands.source == "existing":
            return _discover_prepared_ligands(pcfg)"""
        output_dir = pcfg.common.output_dir
        suffix = pcfg.common.suffix
        n_jobs = pcfg.ligdock.n_jobs

        if pcfg.ligdock.source == "sdf":
            @python_parallel(n_jobs=n_jobs, title="load_sdf_parallel()", skip=True)
            def _load_sdf_parallel(sdfs):
                from nexus.prep.ligdock._load_sdf import _load_sdf
                tasks = []
                for sdf in sdfs:
                    tasks.append(partial(_load_sdf, sdf))
                return tasks

            parallel_output = _load_sdf_parallel(pcfg.common.input)
            mol_with_h_list, names = map(list, zip(*parallel_output))
            

        if pcfg.ligdock.source == "smiles":
            smiles_list, names = _parse_ligands_csv(pcfg.common.input)

            @python_parallel(n_jobs=n_jobs, title="rdkit_gen3d_parallel()", skip=True)
            def _rdkit_gen3d_parallel(smiles_list):
                from nexus.prep.ligdock._rdkit_gen3d import _rdkit_gen3d
                tasks = []
                for smiles in smiles_list:
                    tasks.append(partial(_rdkit_gen3d, smiles))
                return tasks
            mol_with_h_list = _rdkit_gen3d_parallel(smiles_list)


        if Path(suffix).suffix == ".pdbqt":
            @python_parallel(n_jobs=n_jobs, title="meeko_charge_parallel()", skip=True)
            def _meeko_charge_parallel(mol_with_h_list, output_list):
                from nexus.prep.ligdock._meeko_charge import _meeko_charge
                tasks = []
                for mol_with_h, output_path in zip(mol_with_h_list, output_list):
                    tasks.append(partial(
                        _meeko_charge,
                        mol_with_h,
                        output_path
                    ))
                return tasks
            output_list = [output_dir / f"{name}{suffix}" for name in names]
            prepared_ligs = _meeko_charge_parallel(mol_with_h_list, output_list)
        
        
        if Path(suffix).suffix == ".mol2":
            prepared_ligs = []
            tmp_sdf_list = []
            @gnu_parallel(n_jobs=n_jobs, title="obabel_charge_parallel()")
            def _obabel_charge_parallel(mol_with_h_list, names):
                from rdkit import Chem
                cmds = []
                
                for mol_with_h, name in zip(mol_with_h_list, names):
                    tmp_sdf_path = output_dir / f"{name}_nocharge.sdf"
                    tmp_sdf_list.append(tmp_sdf_path)
                    
                    writer = Chem.SDWriter(tmp_sdf_path)
                    writer.write(mol_with_h)

                    output_mol2_path = output_dir / f"{name}{suffix}"
                    cmds.append([
                        "obabel",
                        tmp_sdf_path,
                        "-O", output_mol2_path,
                        "--ff", "mmff94",
                    ])
                    prepared_ligs.append(output_mol2_path)
                return cmds
            
            _obabel_charge_parallel(mol_with_h_list, names)
            for tmp_sdf_path in tmp_sdf_list:
                Path(tmp_sdf_path).unlink(missing_ok=True)

        return prepared_ligs
    return _run()