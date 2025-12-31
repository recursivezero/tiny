import importlib.metadata
import os

import click

from app.app import app

# load_dotenv()

DEFAULT_HOST = os.getenv("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("PORT", "8000"))


@click.group()
@click.version_option(
    importlib.metadata.version("tiny"),
    "--version",
    "-v",
    prog_name="tiny",
    message="tiny version: %(version)s",
)
def main():
    """tiny command-line interface."""
    pass


@main.command()
@click.option("--host", default=DEFAULT_HOST)
@click.option("--port", default=DEFAULT_PORT)
@click.option("--debug", is_flag=True)
def serve(host, port, debug):
    """Start Flask server."""
    app.run(
        host=host,
        port=port,
        debug=debug,
    )


@main.command()
def dev():
    """Run development server with debug enabled."""
    app.run(
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        debug=True,
    )


if __name__ == "__main__":
    main()
