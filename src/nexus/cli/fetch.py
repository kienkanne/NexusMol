import typer
from typing import Optional, List
from pathlib import Path
from nexus.fetch.fetch_config import load_fetch_config, FetchConfig
from nexus.fetch.pipeline import FetchPipeline


app = typer.Typer(help="Run fetch protein and ligand (noncovalent only) structures from RCSB pipelines")

@app.command()
def rcsb(config: Optional[Path] = typer.Option(None, "-c", "--config", help="Path to config YAML"),
         input: Optional[List[str]] = typer.Option(None, "-i", "--input", help="Input PDB ids or text file containing id in each row"),
         ouput_dir: Optional[Path] = typer.Option(None, "-o", "--output_dir", help="Output directory"),
         ligand_name: Optional[bool] = typer.Option(False, "-l", "--ligand_name", help="Option to include ligand name from CCD in output file")):
    """Run the fetch from RCSB pipeline."""

    fcfg = FetchConfig(
        input=input,
        output_dir=ouput_dir,
        ligand_name=ligand_name
    )
    print (input)
    FetchPipeline(fcfg=fcfg).run()
