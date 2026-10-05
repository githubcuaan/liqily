import typer

app = typer.Typer(help="Liqi data CLI")


@app.callback()
def main():
    """Liqi data commands."""


@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    }
)
def discover(ctx: typer.Context):
    """Probe Fandom API and save discovery responses."""
    from .sources.fandom.discover import main as discover_main

    raise typer.Exit(code=discover_main(ctx.args))


if __name__ == "__main__":
    app()
