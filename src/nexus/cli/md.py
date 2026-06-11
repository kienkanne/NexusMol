import typer
from pathlib import Path
from nexus.core.utils.load_config import load_config


app = typer.Typer(help="Run molecular dynamics pipelines")


@app.command()
def run(config: Path = typer.Option(..., "-c", "--config", help="Path to md config YAML")):
    """Run the molecular dynamics pipeline."""
    from nexus.md.run.md_config import MDConfig
    cfg: MDConfig = load_config(MDConfig, config)

    if cfg.engine.program == "amber":
        from nexus.md.run.amber.amber_pipeline import AmberPipeline
        AmberPipeline(cfg=cfg)._run()

    elif cfg.engine.program == "openmm":
        from nexus.md.run.openmm.openmm_pipeline import OpenMMPipeline
        OpenMMPipeline(cfg=cfg)._run()


@app.command()
def build(config: Path = typer.Option(..., "-c", "--config", help="Path to md build config YAML")):
    """Run the build md system pipeline"""
    from nexus.md.build.build_pipeline import BuildPipeline, BuildConfig
    BuildPipeline(cfg=load_config(BuildConfig, config))._run()


@app.command()
def analyze(config: Path = typer.Option(..., "-c", "--config", help="Path to md analysis config YAML")):
    """Run the md analysis pipeline"""
    from nexus.md.analyze.analyze_pipeline import AnalyzePipeline
    from nexus.md.analyze.analyze_config import AnalyzeConfig
    AnalyzePipeline(cfg=load_config(AnalyzeConfig, config))._run()


@app.command()
def mmpbsa(config: Path = typer.Option(..., "-c", "--config", help="Path to md analysis config YAML")):
    """Run the mmpbsa pipeline"""
    from nexus.md.mmpbsa.mmpbsa_pipeline import MMPBSAPipeline
    from nexus.md.mmpbsa.mmpbsa_config import MMPBSAConfig
    MMPBSAPipeline(cfg=load_config(MMPBSAConfig, config))._run()
