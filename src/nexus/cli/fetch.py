import typer
from typing import Optional, List
from pathlib import Path


app = typer.Typer(help="Run fetch protein and ligand (noncovalent only) structures from RCSB pipelines")


def merge_cli_overrides(config, common_flags: dict, unique_key: str = None, unique_flags: dict = None):
    from nexus.fetch.fetch_config import FetchConfig
    """Helper function to handle Pydantic deep merging"""
    from nexus.core.utils.load_config import load_config
    from nexus.fetch.fetch_config import FetchConfig

    cfg = load_config(FetchConfig, config) if (config and config.exists()) else FetchConfig()

    cli_overrides = {k: v for k, v in common_flags.items() if v is not None}
        
    full_data = cfg.model_dump()
    for key, value in cli_overrides.items():
            if isinstance(value, dict):
                full_data[key] = {**full_data.get(key, {}), **value}
            else:
                full_data[key] = value

    return FetchConfig.model_validate(full_data)


@app.command()
def rcsb(config: Optional[Path] = typer.Option(None, "-c", "--config", help = "Path to config YAML"),
         input: Optional[List[str]] = typer.Option(None, "-i", "--input", help="Input PDB ids or text file containing id in each row"),
         output_dir: Optional[Path] = typer.Option(None, "-o", "--output_dir", help="Output directory"),
         ligand_name: Optional[str] = typer.Option(None, "-l", "--ligand_name", help="Option to include ligand name from CCD in output file")):
    """Run the fetch from RCSB pipeline."""

    cfg = merge_cli_overrides(
        config,
        {"input": input, "output_dir": output_dir, "ligand_name": ligand_name}
	)
    
    from nexus.fetch.fetch_pipeline import FetchPipeline
    FetchPipeline(cfg=cfg)._run()
