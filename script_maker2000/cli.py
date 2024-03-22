import click
from pathlib import Path
import tarfile

import pandas as pd
from script_maker2000.config_maker import app, add_main_config
from script_maker2000.files import check_config, collect_input_files
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
def start_config(config):
    """Start the batch manager with the given config file."""
    if not Path(config).exists():
        click.echo(f"Config file not found at {config}")

        return 1

    check_config(main_config=config)
    batch_manager = BatchManager(config)
    batch_manager.run_batch_processing()


@script_maker_cli.command()
@click.option("--tar", "-t", help="Path to the tarball with the input files.")
@click.option(
    "--extract_path",
    "-e",
    default="input_files",
    help="Path where the tar ball is extracted and the sub_dirs for the calculation are generated.",
)
def start_tar(tar, extract_path):
    """Start the batch processing with the given tarball."""

    extract_path = Path(extract_path)
    extract_path = extract_path.resolve()

    with tarfile.open(tar, "r:gz") as tar:
        tar.extractall(path=extract_path, filter="fully_trusted")

    config_path = list(Path(extract_path).glob("*.json"))[0]

    # search for new xyz files and update the csv file
    csv_file = list(Path(extract_path).glob("*.csv"))[0]
    df_mol = pd.read_csv(csv_file)

    for xyz_id in df_mol["key"]:

        xyz_path = list(extract_path.glob(f"**/*{xyz_id}.xyz"))[0]
        if xyz_path.exists():
            df_mol.loc[df_mol["key"] == xyz_id, "path"] = str(xyz_path)
    df_mol.to_csv(csv_file, index=False)

    batch_manager = BatchManager(config_path)
    batch_manager.run_batch_processing()


@script_maker_cli.command()
@click.option("--config", "-c", default="config.json", help="Path to the config file")
@click.option(
    "--output", "-o", default="input_files", help="Path where the tar ball is created."
)
def collect_input(config, output):
    """Will search the config file for input files and prepares a tar ball with all the files."""

    prep_path = Path(output)
    prep_path = prep_path.resolve()
    prep_path.mkdir(exist_ok=True, parents=True)

    config_path = Path(config)

    tar_path = collect_input_files(config_path, prep_path)
    click.echo(f"Tarball created at {tar_path}")
    click.echo(
        "The tarball will contain all the input files needed for the batch processing."
    )
    click.echo("Please move the tarball to the remote server and extract it there.")
    click.echo(
        "To copy the tarball to the remote server you can use the following command:"
    )
    click.echo("scp -P <port> <local_file> <remote_user>@<remote_host>:<remote_path>")
    click.echo(
        "To start the batch processing on the remote server, run the following command:"
    )
    click.echo("python script_maker2000.py start --tar <tar_path>")
    click.echo(
        "The tar ball will be automatically extracted and the batch processing will start."
    )

    return 0
