import click
from pathlib import Path

from script_maker2000.config_maker import app, add_main_config
from script_maker2000.files import check_config
from script_maker2000 import BatchManager


@click.group()
def script_maker_cli():
    pass


@script_maker_cli.command()
@click.help_option("--help", "-h", help="Show this message and exit")
@click.option("--port", "-p", default=8050, help="Port to run the dash server on.")
def config_creator(port):
    """ "This tool is used to create a new config file for the script_maker2000" """
    add_main_config(app)
    app.run_server(debug=True, port=port)


@script_maker_cli.command()
@click.option("--config", "-c", default="config.json", help="Path to the config file")
def config_check(config):
    check_config(main_config=config)
    return 0


@script_maker_cli.command()
@click.option("--config", "-c", default="config.json", help="Path to the config file")
def start(config):
    """Start the batch manager with the given config file."""
    if not Path(config).exists():
        click.echo(f"Config file not found at {config}")

        return 1

    check_config(main_config=config)
    batch_manager = BatchManager(config)
    batch_manager.run_batch_processing()
