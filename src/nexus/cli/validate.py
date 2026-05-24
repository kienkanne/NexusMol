import typer
from pathlib import Path
from nexus.validate.validate_config import load_validate_config
from nexus.validate.rmsd import compute_validation_rmsds

app = typer.Typer(help="Run docking validation pipelines. Currently disabled")

@app.command()
def vina(config: Path = typer.Option(..., "-c", "--config", help="Path to config YAML")):
    """Run the Vina validate docking pipeline. Currently disabled"""
    return None
    from nexus.dock.vina.pipeline import VinaPipeline
    VinaPipeline(load_validate_config(config)).run()
    compute_validation_rmsds(load_validate_config(config))

@app.command()
def dock6(config: Path = typer.Option(..., "-c", "--config")):
    """Run the DOCK6 validate docking pipeline. Currently disabled"""
    return None
    from nexus.dock.dock6.pipeline import DOCK6Pipeline
    DOCK6Pipeline(load_validate_config(config)).run()
    compute_validation_rmsds(load_validate_config(config))