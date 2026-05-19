from dataclasses import dataclass
from pathlib import Path
from string import Template
from compdd.executors.shell import shell
from compdd.executors.base import base
from compdd.utils.main_tracker import main_tracker


@dataclass(frozen=True)
class VinaReceptorBundle:
    receptor: Path
    vina_config: Path
    name: str


def _prep_rec(cfg, receptor):
    name = Path(receptor).stem
    suffix = cfg.common.prepared_suffix
    cleaned_receptor_pdb = f"{name}_{suffix}.pdb"
    prepped_receptor_pdbqt = f"{name}_{suffix}.pdbqt"

    @shell(cfg)
    def clean_rec():
        chimerax = cfg.libs.chimerax

        with open(Path(__file__).resolve().parents[0] / "templates" / "clean_rec_template.com") as f:
            vina_charge_rec_template = f.read()     

        stdin = Template(vina_charge_rec_template).substitute(
            receptor=receptor,
            cleaned_receptor_pdb=cleaned_receptor_pdb,
        )

        return ([chimerax, "--nogui"], stdin)
    clean_rec()


    @shell(cfg)
    def meeko_prep_rec():
        import pymol2
        padding = cfg.common.padding

        if cfg.receptors.pocket_option == "reference":
            if cfg.receptors.reference is None:
                raise ValueError("receptors.reference is required when pocket_option is 'reference'")
            input_file = cfg.receptors.reference
            pocket_selection = "all"
        else:
            if cfg.receptors.pocket_selection is None:
                raise ValueError("receptors.pocket_selection is required when pocket_option is 'selection'")
            input_file = cleaned_receptor_pdb
            pocket_selection = cfg.receptors.pocket_selection

            with pymol2.PyMOL() as pymol:
                pymol.start()
                pymol.cmd.load(input_file, "target")
                pymol.cmd.select("to_delete", f"target and not ({pocket_selection})")
                pymol.cmd.remove("to_delete")
                pymol.cmd.save(f"{name}_pocket.pdb", "target")

        cmd = [
                "mk_prepare_receptor.py",
                "-i",
                cleaned_receptor_pdb,
                "-o",
                f"{name}_{suffix}",
                "-p",  # Generate receptor PDBQT
                "-v",
                f"{name}_{suffix}_vina_config.txt",  # Generate Vina config file
                "--box_enveloping",
                f"{name}_pocket.pdb",  # Wrap around this molecule
                "--padding",
                str(padding),  # Padding buffer in Angstroms
            ]
        
        return (cmd, None)
    meeko_prep_rec()

    @base(cfg, "add_configs()")
    def add_configs():
        exhaustiveness = cfg.vina.exhaustiveness
        num_modes = cfg.vina.num_modes
        extra_configs = {
                    "exhaustiveness": exhaustiveness,
                    "num_modes": num_modes,
                }
        with open(f"{name}_{suffix}_vina_config.txt", "a") as config_file:
            config_file.write("\n")
            for key, value in extra_configs.items():
                config_file.write(f"{key} = {value}\n")
    add_configs()       

    return VinaReceptorBundle(
        receptor=Path(prepped_receptor_pdbqt),
        vina_config=Path(f"{name}_{suffix}_vina_config.txt"),
        name=name,
    )


from compdd.executors.python_parallel import python_parallel
from compdd.utils.main_tracker import main_tracker
from compdd.utils.extract_files import extract_files
from functools import partial


def vina_receptors_prep(cfg):
    @main_tracker(cfg, "Prepare receptor for Vina")
    @python_parallel(cfg, "prep_rec()")
    def _run():
        receptors = extract_files(cfg.receptors.pdbs, ".pdb")
        tasks = []
        for receptor in receptors:
            tasks.append(partial(_prep_rec, cfg, receptor))
        return tasks
    return _run()
