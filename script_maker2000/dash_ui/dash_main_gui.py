from dash import Dash, html
import dash_bootstrap_components as dbc
from script_maker2000.dash_ui.config_maker_ui import (
    create_config_manager_layout,
    add_callbacks,
)
from script_maker2000.dash_ui.remote_explorer import (
    create_manager_layout,
    add_callbacks_remote_explorer,
)
from script_maker2000.dash_ui.results_window import (
    create_results_layout,
    add_callbacks_results,
)

from script_maker2000.dash_ui.slurm_watch_ui import (
    create_slurm_watcher_layout,
    add_callbacks_slurm_watcher,
)


def create_main_app(file_path: str, remote_connection):

    app = Dash("Test", external_stylesheets=[dbc.themes.LITERA])
    config_div = create_config_manager_layout(file_path)
    remote_explorer_layout = create_manager_layout()
    slurm_watch_layout = create_slurm_watcher_layout()

    results_window = create_results_layout()

    tabs = dbc.Tabs(
        [
            dbc.Tab(
                tab_id="config",
                label="Config",
                children=[config_div],
                style={"padding-top": "20px"},
            ),
            dbc.Tab(
                tab_id="managment",
                label="Managment",
                children=[remote_explorer_layout],
                style={"padding-top": "20px"},
            ),
            dbc.Tab(
                tab_id="slurm_watcher",
                label="Slurm Watcher",
                children=[slurm_watch_layout],
                style={"padding-top": "20px"},
            ),
            dbc.Tab(
                tab_id="results",
                label="Results",
                children=[results_window],
                style={"padding-top": "20px"},
            ),
        ],
        active_tab="config",
    )

    hover_layout = create_hover_text_field()

    app.layout = html.Div(
        id="main_div", children=[tabs, hover_layout], style={"padding": "20px"}
    )
    app = add_callbacks(app)

    # this is only for tests
    if remote_connection is None:
        return app

    app = add_callbacks_remote_explorer(app, remote_connection)
    app = add_callbacks_results(app, remote_connection)
    app = add_callbacks_slurm_watcher(app, remote_connection)

    return app


# config_name_input
# input_file_path_input
# parallel_layer_run_input
# wait_for_results_time_input
# continue_previous_run_input
# max_n_jobs_input
# max_compute_nodes_input
# max_cores_per_node_input
# max_ram_per_core_input
# max_run_time_input
# orca_version_input
# run_checks_input
# run_benchmark_input
# {'type': 'layer_name_input', 'index': '0'}
# {'type': 'type_input', 'index': '0'}
# {'type': 'step_id_input', 'index': '0'}
# {'type': 'method_input', 'index': '0'}
# {'type': 'basisset_input', 'index': '0'}
# {'type': 'additional_settings_input', 'index': '0'}
# {'type': 'automatic_ressource_allocation_input', 'index': '0'}
# {'type': 'ram_per_core_input', 'index': '0'}
# {'type': 'n_cores_per_calculation_input', 'index': '0'}
# {'type': 'disk_storage_input', 'index': '0'}
# {'type': 'walltime_input', 'index': '0'}
# {'type': 'layer_name_input', 'index': '1'}
# {'type': 'type_input', 'index': '1'}
# {'type': 'step_id_input', 'index': '1'}
# {'type': 'method_input', 'index': '1'}
# {'type': 'basisset_input', 'index': '1'}
# {'type': 'additional_settings_input', 'index': '1'}
# {'type': 'automatic_ressource_allocation_input', 'index': '1'}
# {'type': 'ram_per_core_input', 'index': '1'}
# {'type': 'n_cores_per_calculation_input', 'index': '1'}
# {'type': 'disk_storage_input', 'index': '1'}
# {'type': 'walltime_input', 'index': '1'}


def create_new_hover_text(popover_header: str, popover_body: str, target_id):

    return dbc.Popover(
        [
            dbc.PopoverHeader(popover_header),
            dbc.PopoverBody(popover_body),
        ],
        target=target_id,
        trigger="hover",
    )


def create_hover_text_field():

    hover_layout = []

    config_name_input_hover = create_new_hover_text(
        popover_header="Enter a config name",
        popover_body="The name of the config file will be used to "
        + "save the config file and to identify the different calculations.",
        target_id="config_name_input",
    )
    hover_layout.append(config_name_input_hover)

    input_file_path_input_hover = create_new_hover_text(
        popover_header="Enter a file path",
        popover_body="Enter the path of a directory that contains xyz files."
        + " Please note that the file names should end with _cXmY.xyz "
        + "where X and Y are the charge and multiplicity of the molecule.",
        target_id="input_file_path_input",
    )
    hover_layout.append(input_file_path_input_hover)

    parallel_layer_run_input_hover = create_new_hover_text(
        popover_header="Enable or disable parallel layers.",
        popover_body="When enabled layers with same step id will be executed in parallel.",
        target_id="parallel_layer_run_input",
    )
    hover_layout.append(parallel_layer_run_input_hover)

    wait_for_results_time_input_hover = create_new_hover_text(
        popover_header="Enter the waiting time for results",
        popover_body="The time the script will wait to refresh results. 30 Seconds is recommended.",
        target_id="wait_for_results_time_input",
    )
    hover_layout.append(wait_for_results_time_input_hover)

    continue_previous_run_input_hover = create_new_hover_text(
        popover_header="Continue previous run",
        popover_body="Not recommended for use in the gui.",
        target_id="continue_previous_run_input",
    )
    hover_layout.append(continue_previous_run_input_hover)

    max_n_jobs_input_hover = create_new_hover_text(
        popover_header="Enter the maximum number of jobs for this calculation run at the same time.",
        popover_body="For large datasets this will limit the number of submissions done at the same time.",
        target_id="max_n_jobs_input",
    )
    hover_layout.append(max_n_jobs_input_hover)

    max_compute_nodes_input_hover = create_new_hover_text(
        popover_header="Enter the maximum number of compute nodes for the entire calculation run.",
        popover_body="When using the automatic resource allocation,"
        + " this will be the maximum number of compute nodes that can be reserved by the program."
        + "Depending on the number of jobs this could override the max_n_jobs_input value"
        + " to avoid exceeding the max number of reserved nodes.",
        target_id="max_compute_nodes_input",
    )
    hover_layout.append(max_compute_nodes_input_hover)

    max_cores_per_node_input_hover = create_new_hover_text(
        popover_header="Enter the maximum number of cores per compute node.",
        popover_body="The maximum number of cores that can be used per compute node.",
        target_id="max_cores_per_node_input",
    )
    hover_layout.append(max_cores_per_node_input_hover)

    max_ram_per_core_input_hover = create_new_hover_text(
        popover_header="Enter the maximum ram per core.",
        popover_body="The maximum amount of ram that will be allocated by the automatic ressource allocation tool."
        + "(default 4GB for normal nodes and 8gb for large nodes)\n"
        + "This value is for each individual calculation.",
        target_id="max_ram_per_core_input",
    )
    hover_layout.append(max_ram_per_core_input_hover)

    max_run_time_input_hover = create_new_hover_text(
        popover_header="Enter the maximum wall time.",
        popover_body="If a calculations runs into the set walltime this"
        + " max value will be used to restart the calculation once.",
        target_id="max_run_time_input",
    )
    hover_layout.append(max_run_time_input_hover)

    orca_version_input_hover = create_new_hover_text(
        popover_header="Enter the orca version.",
        popover_body="The version of orca that will be used for the calculations."
        + " Must be available on the remote server.",
        target_id="orca_version_input",
    )
    hover_layout.append(orca_version_input_hover)

    run_checks_input_hover = create_new_hover_text(
        popover_header="Run checks",
        popover_body="Not yet implemented.",
        target_id="run_checks_input",
    )
    hover_layout.append(run_checks_input_hover)

    run_benchmark_input_hover = create_new_hover_text(
        popover_header="Run benchmark",
        popover_body="Not yet implemented.",
        target_id="run_benchmark_input",
    )
    hover_layout.append(run_benchmark_input_hover)

    layer_name_input_hover = create_new_hover_text(
        popover_header="Enter the layer name",
        popover_body="The name of the layer that will be executed.",
        target_id={"type": "layer_name_input", "index": "0"},
    )
    hover_layout.append(layer_name_input_hover)

    type_input_hover = create_new_hover_text(
        popover_header="Enter the type of calculation",
        popover_body="The type of calculation that will be executed.",
        target_id={"type": "type_input", "index": "0"},
    )
    hover_layout.append(type_input_hover)

    step_id_input_hover = create_new_hover_text(
        popover_header="Enter the step id",
        popover_body="The step id of the calculation. When using parallel layers, "
        + "layers with the same step id will be executed in parallel.",
        target_id={"type": "step_id_input", "index": "0"},
    )
    hover_layout.append(step_id_input_hover)

    method_input_hover = create_new_hover_text(
        popover_header="Enter the method",
        popover_body="The method that will be used for the calculation. \n"
        + "For example: B3LYP, PBE0, M06-2X, etc.",
        target_id={"type": "method_input", "index": "0"},
    )
    hover_layout.append(method_input_hover)

    basisset_input_hover = create_new_hover_text(
        popover_header="Enter the basis set",
        popover_body="The basis set that will be used for the calculation.\n"
        + "For example: def2-SVP, def2-TZVP, etc. but can also be left empty.",
        target_id={"type": "basisset_input", "index": "0"},
    )
    hover_layout.append(basisset_input_hover)

    additional_settings_input_hover = create_new_hover_text(
        popover_header="Enter additional settings",
        popover_body="Additional settings that will be used for the calculation.\n"
        + "For example: D3, RIJCOSX, opt, freq, TightSCF, etc. but can also be left empty.",
        target_id={"type": "additional_settings_input", "index": "0"},
    )
    hover_layout.append(additional_settings_input_hover)

    automatic_ressource_allocation_input_hover = create_new_hover_text(
        popover_header="Automatic resource allocation",
        popover_body="If set to true, the program will try to allocate the resources automatically. \n"
        + "The more calculations are running at the same time the more efficient"
        + " it is to use fewer cores per calculation./n"
        + "For normal nodes the default is 4GB per core and for large nodes 8GB per core.",
        target_id={"type": "automatic_ressource_allocation_input", "index": "0"},
    )
    hover_layout.append(automatic_ressource_allocation_input_hover)

    ram_per_core_input_hover = create_new_hover_text(
        popover_header="Enter the ram per core",
        popover_body="The amount of ram that will be allocated per core."
        + " Only used when automatic resource allocation is set to manual.",
        target_id={"type": "ram_per_core_input", "index": "0"},
    )
    hover_layout.append(ram_per_core_input_hover)

    n_cores_per_calculation_input_hover = create_new_hover_text(
        popover_header="Enter the number of cores per calculation",
        popover_body="The number of cores that will be used for the calculation."
        + " Only used when automatic resource allocation is set to manual.",
        target_id={"type": "n_cores_per_calculation_input", "index": "0"},
    )
    hover_layout.append(n_cores_per_calculation_input_hover)

    disk_storage_input_hover = create_new_hover_text(
        popover_header="Enter the disk storage",
        popover_body="The amount of disk storage that will be used for the calculation. "
        + "Default 0 for ram scratch only.",
        target_id={"type": "disk_storage_input", "index": "0"},
    )
    hover_layout.append(disk_storage_input_hover)

    walltime_input_hover = create_new_hover_text(
        popover_header="Enter the walltime",
        popover_body="The time that will be used for this calculation layer.\n"
        + "When encountering a walltime error the calculation will be restarted with the max walltime value.",
        target_id={"type": "walltime_input", "index": "0"},
    )
    hover_layout.append(walltime_input_hover)

    return html.Div(hover_layout)
