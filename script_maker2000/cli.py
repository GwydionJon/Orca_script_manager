import click
from clickqt import qtgui_from_click
from pathlib import Path
from click_option_group import optgroup
from script_maker2000.config_maker import app, add_main_config


@click.command()
def open_dash():
    add_main_config(app)
    app.run_server(debug=True)


@click.group()
def config():
    print()


@config.command()
@optgroup.group("main_config")
@optgroup.option(
    "-o",
    "--output",
    prompt=True,
    type=click.Path(
        exists=True, resolve_path=True, file_okay=True, dir_okay=False, path_type=Path
    ),
    help="Output file path",
)
@optgroup.option(
    "-i",
    "--input",
    prompt=True,
    type=click.Path(
        exists=True, resolve_path=True, file_okay=True, dir_okay=False, path_type=Path
    ),
    help="Input file path. This should be a csv file with filenames, charge and multiplicity."
    + "The file should have the following columns: 'filename', 'charge', 'multiplicity'",
)
@optgroup.option(
    "--parallel_layer_run",
    prompt=True,
    type=click.BOOL,
    default=False,
    help="Boolean value to determine if layers can be parallel to each other."
    + " For example when two optimisations should be followed by the same sp.",
)
@optgroup.option(
    "--common_input_files",
    prompt=True,
    type=click.STRING,
    multiple=True,
    default=["xyz"],
    help="List of common input files for all layers. For example: --common_input_files file1 file2 file3",
)
@optgroup.option(
    "--max_run_time",
    prompt=True,
    type=click.DateTime(formats=["%d-%H:%M:%S"]),
    default="1-12:00:00",
    help="Maximum run time given as a string in the format 'D-HH:MM:SS'",
)
@optgroup.option(
    "--wait_for_results_time",
    prompt=True,
    type=click.INT,
    default=60,
    help="Time to wait for results in seconds",
)
@optgroup.group("structure_check_config")
@optgroup.option(
    "--run_checks",
    prompt=True,
    default=False,
    type=click.BOOL,
    help="Boolean value to determine if structure check should be performed",
)
@optgroup.group("analysis config")
@optgroup.option(
    "--run_benchmark",
    prompt=True,
    default=False,
    type=click.BOOL,
    help="Boolean value to determine if benchmark analysis should be performed",
)
def create_main_config(**params):

    print("test cli:", params)


@config.command()
@click.option(
    "--layer_name",
    prompt=True,
    type=click.STRING,
    help="Name of the layer",
)
def create_layer_config(**params):
    print("test create layer:", params)


config.add_command(create_main_config)
config.add_command(create_layer_config)
option = click.Option(
    param_decls=["--my_option"], prompt=True, type=click.STRING, help="My option"
)
create_layer_config.params.append(option)


ui_handle = qtgui_from_click(config)
