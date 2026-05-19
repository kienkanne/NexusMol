from functools import partial

from compdd.executors.python_parallel import python_parallel
from compdd.executors.gnu_parallel import gnu_parallel
from compdd.utils.main_tracker import main_tracker

from compdd.ligands._ligands_common import _parse_ligands_csv, _discover_prepared_ligands


def ligands_prep(cfg):
    @main_tracker(cfg, "Prepare ligands")
    def _run():
        if cfg.ligands.source == "existing":
            return _discover_prepared_ligands(cfg)
        
        if cfg.ligands.source == "sdf":
            from compdd.ligands._load_sdf import _load_sdf
            mol_with_h_list, names = _load_sdf(cfg.ligands.sdf_dir)
            
        if cfg.ligands.source == "smiles":
            smiles_list, names = _parse_ligands_csv(cfg.ligands.smiles_csv)

            @python_parallel(cfg, "rdkit_gen3d_parallel()")
            def _rdkit_gen3d_parallel(smiles_list):
                from compdd.ligands._rdkit_gen3d import _rdkit_gen3d
                tasks = []
                for smiles in smiles_list:
                    tasks.append(partial(_rdkit_gen3d, smiles))
                return tasks
            mol_with_h_list = _rdkit_gen3d_parallel(smiles_list)

        if cfg.common.program == "vina":
            @python_parallel(cfg, "meeko_charge_parallel()")
            def _meeko_charge_parallel(mol_with_h_list, names):
                from compdd.ligands._meeko_charge import _meeko_charge
                tasks = []
                for mol_with_h, name in zip(mol_with_h_list, names):
                    tasks.append(partial(
                        _meeko_charge,
                        mol_with_h,
                        name,
                        cfg.ligands.output_dir,
                        cfg.common.prepared_suffix,
                    ))
                return tasks

            prepared_ligs = _meeko_charge_parallel(mol_with_h_list, names)
        
        
        if cfg.common.program == "dock6":
            prepared_ligs = []

            @gnu_parallel(cfg, "obabel_charge_parallel()")
            def _obabel_charge_parallel(mol_with_h_list, names):
                from rdkit import Chem
                obabel = cfg.libs.obabel
                cmds = []
                
                for mol_with_h, name in zip(mol_with_h_list, names):
                        output_nocharge_sdf_path = cfg.common.working_dir / f"{name}_nocharge.sdf"
                        writer = Chem.SDWriter(output_nocharge_sdf_path)
                        writer.write(mol_with_h)

                        output_mol2_path = cfg.ligands.output_dir / f"{name}_{cfg.common.prepared_suffix}.mol2"
                        cmds.append([
                            obabel,
                            output_nocharge_sdf_path,
                            "-O", output_mol2_path,
                            "--ff", "mmff94",
                        ])
                        prepared_ligs.append(output_mol2_path)
                return cmds
            
            _obabel_charge_parallel(mol_with_h_list, names)

        return prepared_ligs
    return _run()