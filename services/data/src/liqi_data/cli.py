import typer

app = typer.Typer(help="Liqi data CLI")


@app.command()
def discover():
    """Probe Fandom API (implemented in step 2)"""
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
