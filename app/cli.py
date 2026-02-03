import click
import uvicorn

from app import __version__
from app.main import app as flask_app


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show Tiny version and exit.")
@click.pass_context
def main(ctx, version):
    """Tiny command-line interface."""
    if version:
        click.echo(__version__)
        ctx.exit()


@main.command()
def dev():
    """Run Tiny Flask UI in development mode."""
    click.echo("🛠 Running Tiny UI (Flask)")
    flask_app.run(host="127.0.0.1", port=8000, debug=True)


@main.command()
def api():
    """Run Tiny API server (FastAPI + uvicorn)."""
    click.echo(f"🚀Tiny API server v{__version__}")
    uvicorn.run(
        "app.api.fast_api:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
    )


if __name__ == "__main__":
    main()
