import typer
from typing import Optional, Annotated, List
from pathlib import Path


app = typer.Typer(help="Run protein and ligand preparation pipelines")


ConfigOpt = Annotated[Optional[Path], typer.Option("-c", "--config", help="Path to config YAML")]
InputOpt = Annotated[Optional[Path], typer.Option("-i", "--input", help="Input file or folder to search for files")]
OutputOpt = Annotated[Optional[Path], typer.Option("-o", "--output_dir", help="Output folder directory")]
SuffixOpt = Annotated[Optional[str], typer.Option("-s", "--suffix", help="Suffix of output file(s)")]



def load_config_overrides(config: Path, common_flags: dict, unique_key: str, unique_flags: dict):
    """Helper function to load prep config and handle cli overrides for Pydantic deep merging"""
    from nexus.core.utils.load_config import load_config
    from nexus.prep.prep_config import PrepConfig

    # The prep command allows the user to use flags directly, so load_config might not be used
    cfg = load_config(PrepConfig, config) if (config and config.exists()) else PrepConfig()

    cli_overrides = {
        "common": {k: v for k, v in common_flags.items() if v is not None},
        unique_key: {k: v for k, v in unique_flags.items() if v is not None}
    }
    full_data = cfg.model_dump()
    for key, sub_dict in cli_overrides.items():
        full_data[key] = {**full_data.get(key, {}), **sub_dict}

    cfg = PrepConfig.model_validate(full_data)

    # Since load_config might not be used, load_global_config is used here
    from nexus.config import load_global_config
    setattr(cfg, "_global", load_global_config())

    return cfg


@app.command()
def rec(
    config: ConfigOpt = None, input: InputOpt = None, output_dir: OutputOpt = None, suffix: SuffixOpt = None,
    dry: bool = typer.Option(False, "-d", "--dry", help="Remove water from protein")
):
    """Run the protein cleaning preparation with ChimeraX pipeline.
    If the input is a folder, all files with '.cif' and '.pdb' are searched to be processed"""
    
    cfg = load_config_overrides(
        config, 
        {"input": input, "output_dir": output_dir, "suffix": suffix}, 
        unique_key="rec", 
        unique_flags={"dry": dry}
    )

    from nexus.prep.rec.pipeline import RecPipeline
    RecPipeline(cfg=cfg)._run()


@app.command()
def mutate(
    config: ConfigOpt = None, input: InputOpt = None, output_dir: OutputOpt = None, suffix: SuffixOpt = None,
    mutations: Optional[List[str]] = typer.Option(None, "-m", "--mutations", help="Syntax must match '{selection}-{NEW_RES}'")
):
    """Change residues identity or protonation state using ChimeraX.
    If the input is a folder, all files with '.cif' and '.pdb' are searched to be processed"""

    cfg = load_config_overrides(
        config, 
        {"input": input, "output_dir": output_dir, "suffix": suffix}, 
        unique_key="mutate", 
        unique_flags={"mutations": mutations}
    )

    from nexus.prep.mutate.pipeline import MutatePipeline
    MutatePipeline(cfg=cfg)._run()
    

@app.command()
def lig(
    config: ConfigOpt = None, input: InputOpt = None, output_dir: OutputOpt = None, suffix: SuffixOpt = None,
    n_jobs: Optional[int] = typer.Option(1, "-n", "--n-jobs", help="Number of ligand preparation jobs to run in paralllel")
):
    """Prepare ligands for docking from SMILES or SDF input."""
    
    cfg = load_config_overrides(
        config, 
        {"input": input, "output_dir": output_dir, "suffix": suffix}, 
        unique_key="lig", 
        unique_flags={"n_jobs": n_jobs}
    )
    
    from nexus.prep.lig.pipeline import LigPipeline
    LigPipeline(cfg=cfg)._run()
