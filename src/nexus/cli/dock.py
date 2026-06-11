import typer
from pathlib import Path
from nexus.core.utils.load_config import load_config


app = typer.Typer(help="Run molecular docking pipelines")


@app.command()
def run(config: Path = typer.Option(..., "-c", "--config", help="Path to dock config YAML")):
    """Run the docking pipeline."""
    from nexus.dock.dock_config import DockConfig
    cfg: DockConfig = load_config(DockConfig, config)

    if cfg.engine.program == "vina":
        from nexus.dock.vina.vina_pipeline import VinaPipeline
        VinaPipeline(cfg)._run()

    elif cfg.engine.program == "dock6":
        from nexus.dock.dock6.dock6_pipeline import DOCK6Pipeline
        DOCK6Pipeline(cfg)._run()
