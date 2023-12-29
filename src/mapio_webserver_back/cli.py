"""Console script for mapio_webserver_back."""

# Standard lib imports
import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional

# Third-party lib imports
import click
from waitress import serve  # type: ignore

from mapio_webserver_back.app.server import create_app


# Define this function as a the main command entrypoint
@click.group()
# Create an argument that expects a path to a valid file
@click.option(
    "--log-config",
    help="Path to the log config file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        writable=False,
        readable=True,
        resolve_path=True,
    ),
)
# Display the help if no option is provided
@click.help_option()
def main(
    log_config: Optional[str],
) -> None:
    """Console script for mapio_webserver_back."""
    if log_config is not None:
        logging.config.fileConfig(log_config)
    else:
        # Default to some basic config
        log_config = f"{Path(__file__).parent}/log.cfg"
        logging.config.fileConfig(log_config)
        tmp_logger = logging.getLogger(__name__)
        tmp_logger.warning("No log config provided, using default configuration")
    logger = logging.getLogger(__name__)
    logger.info("Logger initialized")


@main.command()
def app() -> None:
    logger = logging.getLogger((__name__))
    logger.info("Start server")

    app = create_app()
    serve(app, port=8456, host="0.0.0.0")  # nosec
    # app.run(port=8456, host="0.0.0.0", debug=True)

    logger.info("Server is stopped")


if __name__ == "__main__":
    sys.exit(main())
