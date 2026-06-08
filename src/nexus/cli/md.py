import typer
from pathlib import Path


app = typer.Typer(help="Run molecular dynamics pipelines")

@app.command()
def amber(config: Path = typer.Option(..., "-c", "--config", help="Path to config YAML")):
    """Run the amber MD pipeline."""
    from nexus.md.amber.pipeline import AmberPipeline
    from nexus.md.md_config import load_md_config
    AmberPipeline(mcfg=load_md_config(config))._run()


@app.command()
def openmm(config: Path = typer.Option(..., "-c", "--config", help="Path to config YAML")):
    """Run the openmm MD pipeline."""
    from nexus.md.openmm.pipeline import OpenMMPipeline
    from nexus.md.md_config import load_md_config
    OpenMMPipeline(mcfg=load_md_config(config))._run()


@app.command()
def analyze(
    prmtop: Path = typer.Option(..., "-p", "--prmtop", help="Path to prmtop file"),
    trajin: Path = typer.Option(..., "-t", "--trajin", help="Path to trajectory file"),
    mask: str = typer.Option(..., "-m", "--mask", help="CPPTRAJ mask expression"),
    name: str | None = typer.Option(None, "-n", "--name", help="Analysis name (defaults to prmtop.stem)"),
    output_dir: Path | None = typer.Option(None, "-o", "--output-dir", help="Output directory (defaults to current working directory)"),
):
    """Run full analysis using CPPTRAJ."""
    from nexus.md.analysis.full_analyze import full_analyze

    if name is None:
        name = prmtop.stem
    if output_dir is None:
        output_dir = Path.cwd()

    full_analyze(prmtop=prmtop, trajin=trajin, mask=mask, name=name, output_dir=output_dir)


@app.command()
def fbe(
    prmtop: Path = typer.Option(..., "-p", "--prmtop", help="Path to prmtop file"),
    trajin: Path = typer.Option(..., "-t", "--trajin", help="Path to trajectory file"),
    mask: str = typer.Option(..., "-m", "--mask", help="CPPTRAJ mask expression"),
    name: str | None = typer.Option(None, "-n", "--name", help="Analysis name (defaults to prmtop.stem)"),
    output_dir: Path | None = typer.Option(None, "-o", "--output-dir", help="Output directory (defaults to current working directory)"),
    start_frame: int = typer.Option(1, "-s", "--start-frame", help="Starting frame for MMPBSA analysis"),
    end_frame: int = typer.Option(9999999, "-e", "--end-frame", help="Ending frame for MMPBSA analysis"),
    interval: int = typer.Option(10, "-i", "--interval", help="Frame interval for MMPBSA analysis"),
    n_cores: int = typer.Option(1, "-c", "--n-cores", help="Number of MPI cores to use for MMPBSA")
):
    """Run free binding energy analysis using MMPBSA."""
    from nexus.md.fbe.fbe import fbe

    if name is None:
        name = prmtop.stem
    if output_dir is None:
        output_dir = Path.cwd()

    fbe(prmtop=prmtop, trajin=trajin, mask=mask, name=name, output_dir=output_dir, 
                 startframe=start_frame, endframe=end_frame, interval=interval, n_cores=n_cores)
