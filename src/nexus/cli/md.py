import typer
from pathlib import Path

from nexus.md.md_config import MDConfig, load_md_config

app = typer.Typer(help="Run molecular dynamics pipelines")

@app.command()
def amber(config: Path = typer.Option(..., "-c", "--config", help="Path to config YAML")):
    """Run the amber MD pipeline."""
    from nexus.md.amber.pipeline import AmberPipeline
    AmberPipeline(mcfg=load_md_config(config))._run()


@app.command()
def openmm(config: Path = typer.Option(..., "-c", "--config", help="Path to config YAML")):
    """Run the openmm MD pipeline."""
    print ("Work in progress ...")
    pass
