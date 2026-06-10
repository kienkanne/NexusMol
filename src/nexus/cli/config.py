import typer
import yaml
from pathlib import Path

from nexus.config import (
    get_global_config_path,
    write_default_config,
    load_global_config,
    validate_global_config,
)

app = typer.Typer(name="config", help="Manage global nexus configuration")


@app.command()
def init(force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config")):
    """Create a default global config file if missing."""
    cfg_path = get_global_config_path()
    if cfg_path.exists() and not force:
        typer.echo(f"Config already exists at {cfg_path}")
        raise typer.Exit()

    write_default_config(cfg_path, force=force)
    typer.echo(f"Wrote default config to {cfg_path}. Please edit settings and configure paths here.")


@app.command()
def show():
    """Print the currently loaded global configuration (YAML)."""
    cfg = load_global_config()
    try:
        data = cfg.model_dump(mode="json")
    except Exception:
        data = cfg.__dict__
        
    typer.echo(f"Config path: {get_global_config_path()}")
    typer.echo(yaml.safe_dump(data, sort_keys=False))


@app.command()
def validate():
    """Validate all configured paths in the global configuration."""
    results, has_missing = validate_global_config()

    if not results:
        typer.echo("Configuration is empty or no paths are defined.")
        return

    current_section = None

    for full_key, status in results.items():
        section, field = full_key.split(".", 1)

        if section != current_section:
            current_section = section
            typer.echo(f"\n[{current_section.upper()} CONFIGURATION]")
        
        if status == "OK":
            color = typer.colors.GREEN
        elif status == "Missing path":
            color = typer.colors.RED
        else:
            color = typer.colors.YELLOW

        typer.echo(f"  {field}: ", nl=False)
        typer.secho(status, fg=color)

    if has_missing:
        typer.secho("\nValidation failed: One or more paths are missing.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    
    typer.secho("\nValidation successful!", fg=typer.colors.GREEN)
