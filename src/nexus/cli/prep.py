import typer
from typing import Optional, Literal, Annotated, List
from pathlib import Path
from nexus.prep.prep_config import load_prep_config, PrepConfig


app = typer.Typer(help="Run protein and ligand preparation pipelines")


ConfigOpt = Annotated[Optional[Path], typer.Option("-c", "--config", help="Path to config YAML")]
InputOpt = Annotated[Optional[Path], typer.Option("-i", "--input", help="Input file or folder to search for files")]
OutputOpt = Annotated[Optional[Path], typer.Option("-o", "--output_dir", help="Output folder directory")]
SuffixOpt = Annotated[Optional[str], typer.Option("-s", "--suffix", help="Suffix of output file(s)")]


def merge_cli_overrides(pcfg: PrepConfig, common_flags: dict, unique_key: str, unique_flags: dict) -> PrepConfig:
    """Helper function to handle your Pydantic deep merging"""
    cli_overrides = {
        "common": {k: v for k, v in common_flags.items() if v is not None},
        unique_key: {k: v for k, v in unique_flags.items() if v is not None}
    }
    full_data = pcfg.model_dump()
    for key, sub_dict in cli_overrides.items():
        full_data[key] = {**full_data.get(key, {}), **sub_dict}

    return PrepConfig.model_validate(full_data)


@app.command()
def rec(
    config: ConfigOpt = None, input: InputOpt = None, output_dir: OutputOpt = None, suffix: SuffixOpt = None,
    dry: bool = typer.Option(False, "-d", "--dry", help="Remove water from protein")
):
    """Run the protein cleaning preparation with ChimeraX pipeline."""
    pcfg = load_prep_config(config) if (config and config.exists()) else PrepConfig()
    
    pcfg = merge_cli_overrides(
        pcfg, 
        {"input": input, "output_dir": output_dir, "suffix": suffix}, 
        unique_key="rec", 
        unique_flags={"dry": dry}
    )

    from nexus.prep.rec.pipeline import RecPipeline
    RecPipeline(pcfg=pcfg)._run()


@app.command()
def mutate(
    config: ConfigOpt = None, input: InputOpt = None, output_dir: OutputOpt = None, suffix: SuffixOpt = None,
    mutations: Optional[List[str]] = typer.Option(None, "-m", "--mutations", help="Syntax must match '{selection}&:{RES}-{NEW_RES}'")
):
    """Change residues identity or protonation state using ChimeraX."""
    pcfg = load_prep_config(config) if (config and config.exists()) else PrepConfig()

    pcfg = merge_cli_overrides(
        pcfg, 
        {"input": input, "output_dir": output_dir, "suffix": suffix}, 
        unique_key="mutate", 
        unique_flags={"mutations": mutations}
    )

    from nexus.prep.mutate.pipeline import MutatePipeline
    MutatePipeline(pcfg=pcfg)._run()
    

@app.command()
def ligdock(
    config: ConfigOpt = None, input: InputOpt = None, output_dir: OutputOpt = None, suffix: SuffixOpt = None,
    ctype: Optional[Literal["GAFF", "AM1-BCC"]] = typer.Option("GAFF", "-t", "--ctype", help="Charge type for ligands (wip)")
):
    """Change residues identity or protonation state using ChimeraX."""
    pcfg = load_prep_config(config) if (config and config.exists()) else PrepConfig()
    
    pcfg = merge_cli_overrides(
        pcfg, 
        {"input": input, "output_dir": output_dir, "suffix": suffix}, 
        unique_key="ligdock", 
        unique_flags={"type": ctype}
    )
    
    from nexus.prep.ligdock.pipeline import LigdockPipeline
    LigdockPipeline(pcfg=pcfg)._run()