import typer
from nexus.cli import dock, validate, fetch, prep, md

app = typer.Typer(name="nexus", help="Computational toolkit for drug discovery")
app.add_typer(dock.app,     name="dock")
app.add_typer(validate.app, name="validate")
app.add_typer(fetch.app,    name="fetch")
app.add_typer(prep.app,     name="prep")
app.add_typer(md.app,       name="md")

def main():
    app()


if __name__ == "__main__":
    main()