import typer
from nexus.cli import dock, fetch, prep, md, config
from nexus.core.trackers.logging_utils import set_silence

app = typer.Typer(name="nexus", help="Computational toolkit for drug discovery")
app.add_typer(dock.app,     name="dock")
app.add_typer(fetch.app,    name="fetch")
app.add_typer(prep.app,     name="prep")
app.add_typer(md.app,       name="md")
app.add_typer(config.app,   name="config")


@app.callback(invoke_without_command=True)
def _set_globals(
    silence: int = typer.Option(
        0,
        "--silence",
        help="Silence level: 0=default,1=info-muted,2=all-muted",
    )
):
    """Global CLI options applied before any subcommand runs."""
    set_silence(silence)


def main():
    app()


if __name__ == "__main__":
    main()