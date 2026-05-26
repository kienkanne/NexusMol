import typer
from typing import Optional, List
from pathlib import Path


app = typer.Typer(help="Run fetch protein and ligand (noncovalent only) structures from RCSB pipelines")


def merge_cli_overrides(pcfg, common_flags: dict, unique_key: str = None, unique_flags: dict = None):
    from nexus.prep.prep_config import PrepConfig
    """Helper function to handle Pydantic deep merging"""
    cli_overrides = {k: v for k, v in common_flags.items() if v is not None}
        
    full_data = pcfg.model_dump()
    for key, sub_dict in cli_overrides.items():
        full_data[key] = {**full_data.get(key, {}), **sub_dict}

    return PrepConfig.model_validate(full_data)


@app.command()
def rcsb(config: Optional[Path] = typer.Option(None, "-c", "--config", help = "Path to config YAML"),
         input: Optional[List[str]] = typer.Option(None, "-i", "--input", help="Input PDB ids or text file containing id in each row"),
         output_dir: Optional[Path] = typer.Option(None, "-o", "--output_dir", help="Output directory"),
         ligand_name: Optional[str] = typer.Option(None, "-l", "--ligand_name", help="Option to include ligand name from CCD in output file")):
    """Run the fetch from RCSB pipeline."""

    from nexus.fetch.fetch_config import FetchConfig, load_fetch_config

    fcfg = load_fetch_config(config) if config and Path(config).is_file() else FetchConfig()

    fcfg = merge_cli_overrides(
        fcfg,
        {"input": input, "output_dir": output_dir, "ligand_name": ligand_name}
	)
    
    from nexus.fetch.pipeline import FetchPipeline
    FetchPipeline(fcfg=fcfg).run()
