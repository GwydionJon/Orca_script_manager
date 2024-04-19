import click
from pathlib import Path
import tarfile
import shutil
import json
import cProfile
import atexit

from script_maker2000.dash_ui.dash_main_gui import create_main_app
from script_maker2000.files import (
    check_config,
    collect_input_files,
    read_mol_input_json,
)
from script_maker2000 import BatchManager
from script_maker2000.remote_connection import RemoteConnection


@click.group()
def script_maker_cli():
    pass


@script_maker_cli.command()
@click.help_option("--help", "-h", help="Show this message and exit")
@click.option("--port", "-p", default=8050, help="Port to run the dash server on.")
@click.option(
    "--config",
    "-c",
    default=None,
    help="Path to the config file. If the file does not exist a new file will be created.",
)
@click.option(
    "--hostname",
    "-h",
    default="justus2.uni-ulm.de",
    help="Hostname of the remote server.",
)
# Add the username option and prompt the user for the username
@click.option("--username", "-u", help="Username of the remote server.", prompt=True)
@click.option(
    "--password",
    "-pw",
    help="Password of the remote server.",
    prompt=True,
    hide_input=True,
)
def config_creator(port, config, hostname, username, password):
    """ "This tool is used to create a new config file for the script_maker2000" """

    if config is None:
        # by default read the empty config from data
        config = Path(__file__).parent / "data" / "empty_config.json"

    remote_connection_obj = RemoteConnection()
    remote_connection = remote_connection_obj.connect(username, hostname, password)

    app = create_main_app(config, remote_connection)
    app.run_server(debug=True, port=port, use_reloader=False)


@script_maker_cli.command()
@click.option("--config", "-c", default="config.json", help="Path to the config file")
def config_check(config):
    check_config(main_config=config)
    return 0


@script_maker_cli.command()
@click.option("--config", "-c", default="config.json", help="Path to the config file")
@click.option(
    "--continue_run",
    "-cont",
    is_flag=True,
    flag_value=True,
    type=click.BOOL,
    default=False,
    help="If the batch processing should continue from the last calculation.",
)
@click.option(
    "--profile",
    is_flag=True,
    help="If the code should be profiled. Will create a '.prof' file",
)
def start_config(config, continue_run, profile: bool):
    """Start the batch manager with the given config file."""
    if not Path(config).exists():
        click.echo(f"Config file not found at {config}")

        return 1

    if profile:
        print("Profiling the code")
        pr = cProfile.Profile()
        pr.enable()

        def exit_():
            pr.disable()
            print("Profiling completed")

            pr.dump_stats("profiling_run.prof")

        atexit.register(exit_)

    check_config(main_config=config, override_continue_job=continue_run)

    click.echo(f"Starting the batch processing with the config file at {config}")

    if continue_run:
        click.echo("Continuing from the last calculation.")

    batch_manager = BatchManager(config, override_continue_job=continue_run)

    batch_manager.run_batch_processing()


@script_maker_cli.command()
@click.option("--tar", "-t", help="Path to the tarball with the input files.")
@click.option(
    "--extract_path",
    "-e",
    default="input_files",
    help="Path where the tar ball is extracted and the sub_dirs for the calculation are generated.",
)
@click.option(
    "--remove_extracted",
    "-r",
    is_flag=True,
    flag_value=True,
    type=click.BOOL,
    default=False,
    help="If the extracted files should be removed initilization of the calculation.",
)
@click.option(
    "--profile",
    is_flag=True,
    help="If the code should be profiled. Will create a '.prof' file",
)
def start_tar(tar, extract_path, remove_extracted, profile: bool):
    """Start the batch processing with the given tarball."""

    extract_path = Path(extract_path)
    extract_path = extract_path.resolve()
    extract_path.mkdir(exist_ok=True, parents=True)

    if profile:
        print("Profiling the code")
        pr = cProfile.Profile()
        pr.enable()

        def exit_():
            pr.disable()
            print("Profiling completed")

            pr.dump_stats(extract_path / "profiling_run.prof")

        atexit.register(exit_)

    click.echo(f"Starting the batch processing with the tarball at {tar}.")
    with tarfile.open(tar, "r:gz") as tar:
        tar.extractall(path=extract_path, filter="data")

    click.echo(f"Tarball extracted at {extract_path}")

    json_files = list(Path(extract_path).glob("*.json"))
    if len(json_files) == 0:
        click.echo("No json files found in the extracted folder.")
        return 1

    if len(json_files) > 2:
        click.echo("More than two json files found in the extracted folder.")
        return 1

    config_path = None
    mol_json_path = None

    for file in json_files:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "main_config" in data:
                config_path = file
            else:
                mol_json_path = file

    if config_path is None:
        click.echo("No config file found in the extracted folder.")
        return 1

    if mol_json_path is None:
        click.echo("No molecule json file found in the extracted folder.")
        return 1

    # load config file and replace output path

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    current_output_path = config["main_config"]["output_dir"]
    config["main_config"]["output_dir"] = str(
        extract_path.parents[0] / current_output_path
    )

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    click.echo(f"Config file found at {config_path}")
    click.echo(f"Molecule json file found at {mol_json_path}")

    # skip file check as the extracted config has only vaguely correct file paths
    mol_json = read_mol_input_json(mol_json_path, True)
    # find the xyz files in the extracted folder
    for xyz_id in mol_json.keys():
        click.echo(xyz_id)
        xyz_path = list(extract_path.glob(f"**/*{xyz_id}*.xyz"))[0]
        click.echo(xyz_path)
        if xyz_path.exists():
            mol_json[xyz_id]["path"] = str(xyz_path)

    with open(mol_json_path, "w", encoding="utf-8") as f:
        json.dump(mol_json, f)

    # now check the new config file
    mol_json = read_mol_input_json(mol_json_path)

    click.echo("Updated the path to the xyz files in the csv file.")
    click.echo(f"Found {len(mol_json)} molecules to calculate.")

    batch_manager = BatchManager(config_path)

    if remove_extracted:
        click.echo("Removing the extracted files.")
        shutil.rmtree(extract_path)

    click.echo(f"Output will be saved at {config['main_config']['output_dir']}")
    click.echo("Log files will be saved at in their respective folders.")
    click.echo("Starting the batch processing:")

    exit_code, task_results = batch_manager.run_batch_processing()

    click.echo(f"Batch processing finished with exit code {exit_code}")
    click.echo("Task results:")
    for task in task_results:
        click.echo(task)


@script_maker_cli.command()
@click.option("--config", "-c", default="config.json", help="Path to the config file")
@click.option(
    "--output", "-o", default="input_files", help="Path where the tar ball is created."
)
@click.option(
    "--tar_name",
    "-t",
    default="input_files.tar.gz",
    help="Name of the tar ball with the input files.",
)
def collect_input(config, output, tar_name):
    """Will search the config file for input files and prepares a tar ball with all the files."""

    prep_path = Path(output)
    prep_path = prep_path.resolve()
    prep_path.mkdir(exist_ok=True, parents=True)

    config_path = Path(config)

    tar_path = collect_input_files(config_path, prep_path, tar_name=tar_name)
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
    click.echo(
        "After installing the script_maker2000 package on the remote server run:"
    )
    click.echo(f"script_maker2000 start_tar -t {tar_path.name}")
    click.echo(
        "The tar ball will be automatically extracted and the batch processing will start."
    )

    return 0
