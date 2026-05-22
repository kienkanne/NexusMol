import typer
from pathlib import Path
from nexus.prep.prep_config import load_prep_config
from nexus.prep.chimerax_fix import chimerax_fix

app = typer.Typer(help="Run fetch protein and ligand structures from RCSB pipelines")

@app.command()
def clean(config: Path = typer.Option(..., "-c", "--config", help="Path to config YAML")):
    """Run the protein cleaning preparation with ChimeraX pipeline."""
    chimerax_fix(load_prep_config(config))
