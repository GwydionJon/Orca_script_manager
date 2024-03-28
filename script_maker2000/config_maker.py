import dash
import dash_bootstrap_components as dbc
from collections import defaultdict
import dash_renderjson
import dash_cytoscape as cyto
import json
from dash import Dash, html, dcc, Input, Output, State, MATCH, ALL
from pathlib import Path
from script_maker2000.files import check_config

currently_avaiable_layer_types = ["orca"]
default_style = {"margin": "10px", "width": "100%"}

app = dash.Dash("Config Maker", external_stylesheets=[dbc.themes.DARKLY])

app.layout = html.Div(id="main_div", children=[], style={"padding": "20px"})


def add_main_config(app: Dash) -> Dash:

    main_config_input_group = dbc.Col(
        id="main_config",
        style={"width": "100%"},
        children=[
            dbc.Row(
                children=[
                    dbc.InputGroupText("Config Name"),
                    dbc.Input(
                        id="config_name_input",
                        value="config",
                        type="text",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                children=[
                    dbc.InputGroupText("Relativ output path"),
                    dbc.Input(
                        id="output_path_input",
                        value="output_dir",
                        type="text",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Input Path"),
                    dbc.Input(
                        id="input_path_input",
                        placeholder="Input file path can be absolut or relativ.",
                        type="text",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("XYZ Dir Path"),
                    dbc.Input(
                        id="xyz_dir_path_input",
                        placeholder="XYZ dir path can be absolut or relativ.",
                        type="text",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Parallel Layer Run"),
                    dcc.RadioItems(
                        id="parallel_layer_run_input",
                        options=[
                            {"label": "True", "value": True},
                            {"label": "False", "value": False},
                        ],
                        value=False,
                    ),
                ],
                style={"margin": "10px", "width": "100%", "margin-top": "20px"},
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Continue previous Run"),
                    dcc.RadioItems(
                        id="continue_previous_run_input",
                        options=[
                            {"label": "True", "value": True},
                            {"label": "False", "value": False},
                        ],
                        value=False,
                    ),
                ],
                style={"margin": "10px", "width": "100%", "margin-top": "20px"},
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Input Type"),
                    dcc.RadioItems(
                        id="input_type_input",
                        options=[
                            {"label": "xyz", "value": "xyz"},
                        ],
                        value="xyz",
                    ),
                ],
                style={"margin": "10px", "width": "100%", "margin-top": "20px"},
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Common Input Files: seperate by ,"),
                    dbc.Input(
                        id="common_input_files_input",
                        value="xyz, ",
                        type="text",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Max Run Time [hh:mm:ss]"),
                    dbc.Input(
                        id="max_run_time_input",
                        placeholder="Max Run Time",
                        value="30:00:00",
                        type="text",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Orca Version"),
                    dbc.Input(
                        id="orca_version_input",
                        placeholder="Max Run Time",
                        value="5.0.2",
                        type="text",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Max Run jobs [int]"),
                    dbc.Input(
                        id="max_n_jobs_input",
                        value=100,
                        type="number",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Max ram per core [int]"),
                    dbc.Input(
                        id="max_ram_per_core_input",
                        value=2500,
                        type="number",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Max nodes per job [int]"),
                    dbc.Input(
                        id="max_nodes_input",
                        value=48,
                        type="number",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                [
                    dbc.InputGroupText("Wait For Results Time [s]"),
                    dbc.Input(
                        id="wait_for_results_time_input",
                        placeholder="Wait For Results Time",
                        value=600,
                        min=1,
                        step=30,
                        type="number",
                    ),
                ],
                style=default_style,
            ),
        ],
    )

    accordion = dbc.Accordion(
        [
            dbc.AccordionItem(
                [
                    main_config_input_group,
                ],
                title="Main Config",
            ),
            dbc.AccordionItem(
                [add_structure_check_config()],
                title="Structure Check Config",
            ),
            dbc.AccordionItem(
                [add_analysis_config()],
                title="Analysis Config",
            ),
            dbc.AccordionItem(
                [add_layer_config_layout()],
                title="Layer Config",
            ),
        ],
        style={"width": "90%"},
        id="accordion",
    )

    create_config_file_button = dbc.Button(
        "Check Config File",
        id="create_config_file_button",
        n_clicks=0,
        style={"margin": "10px", "width": "30%"},
    )

    export_config_file_button = dbc.Button(
        "Export Config File",
        id="export_config_file_button",
        n_clicks=0,
        style={"margin": "10px", "width": "30%"},
    )
    download_object = dcc.Download(id="download_config_file")
    button_row = dbc.Row(
        [create_config_file_button, export_config_file_button, download_object]
    )

    empty_div = html.Div(id="empty_div", children=[])

    json_view = dash_renderjson.DashRenderjson(id="json_view")

    acc_column = dbc.Col(accordion, md=4, lg=4, xl=4)
    json_col = dbc.Col(
        [
            button_row,
            dbc.Row(
                dcc.Textarea(
                    id="config_check_output",
                    placeholder="If the config check fails the error will be displayed here.",
                    style={"width": "100%"},
                    disabled=True,
                )
            ),
            dbc.Row(
                id="json_output",
                children=[json_view],
            ),
        ]
    )

    cyto_col = dbc.Col(
        [
            dbc.Row(
                cyto.Cytoscape(
                    id="cytoscape",
                    layout={"name": "cose"},
                )
            ),
            dbc.Row(
                html.Pre(
                    id="cyto_output",
                    style={
                        "width": "100%",
                        "border": "thin lightgrey solid",
                    },
                    children="No config file created yet.",
                ),
                style={
                    "margin": "10px",
                },
            ),
        ]
    )

    new_row = dbc.Row([acc_column, json_col, cyto_col])

    app.layout.children.append(new_row)

    # app.layout.children.append(button_row)

    app.layout.children.append(empty_div)
    app = add_callbacks(app)
    return app


def add_structure_check_config():
    structure_check_config_input_group = dbc.Col(
        id="structure_check_config",
        style={"width": "40%"},
        children=[
            dbc.Row(
                [
                    dbc.InputGroupText("Run Checks"),
                    dbc.Checklist(
                        id="run_checks_input",
                        options={"run checks": "run checks"},
                        switch=True,
                        value=[False],
                    ),
                ],
                style={"margin": "10px", "width": "80%", "margin-top": "20px"},
            ),
        ],
    )

    return structure_check_config_input_group


def add_analysis_config():
    analysis_config_input_group = dbc.Col(
        id="analysis_config",
        style={"width": "40%"},
        children=[
            dbc.Row(
                [
                    dbc.InputGroupText("Run Benchmark"),
                    dbc.Checklist(
                        id="run_benchmark_input",
                        options={"run benchmark": "run benchmark"},
                        switch=True,
                        value=[False],
                    ),
                ],
                style={"margin": "10px", "width": "80%", "margin-top": "20px"},
            ),
        ],
    )

    return analysis_config_input_group


def add_layer_config_layout():
    layer_config_input_group = dbc.Col(
        id="layer_config",
        children=[
            dbc.Row(
                [
                    dbc.InputGroupText("total number of calculation layers"),
                    dbc.Input(
                        id="layer_name_input",
                        value=2,
                        min=1,
                        max=100,
                        type="number",
                    ),
                ],
                style=default_style,
            ),
            dbc.Row(
                id="layer_config_row",
                style=default_style,
                children=[
                    dbc.Accordion(
                        children=[],
                        style={"width": "100%"},
                        id="layer_accordion",
                    )
                ],
            ),
        ],
    )

    return layer_config_input_group


def add_single_layer_config(i: int):

    options_dict = {
        "additional_input_files": "",
        "method": "HF",
        "basisset": "DEF2-SVP",
        "additional_calculation_options": "",
        "ram_per_core": 20,
        "n_cores_per_calculation": 12,
        "n_calculation_at_once": 30,
        "disk_storage": 0,
        "max_run_time": "60:00:00",
    }

    layer_layout = dbc.Col(
        [
            # layer name
            dbc.Row(
                [
                    dbc.InputGroupText("Layer Name"),
                    dbc.Input(
                        id={"type": "layer_name_input", "index": f"{i}"},
                        value=f"layer_name_{i}",
                        type="text",
                    ),
                ],
                style=default_style,
            ),
            # layer type
            dbc.Row(
                [
                    dbc.InputGroupText("Layer Type"),
                    dbc.Select(
                        id={"type": "layer_type_input", "index": f"{i}"},
                        options=[
                            {"label": i, "value": i}
                            for i in currently_avaiable_layer_types
                        ],
                        value="orca",
                    ),
                ],
                style=default_style,
            ),
            # step_id
            dbc.Row(
                [
                    dbc.InputGroupText("Step ID"),
                    dbc.Input(
                        id={"type": "step_id_input", "index": f"{i}"},
                        value=i,
                        min=0,
                        type="number",
                    ),
                ],
                style=default_style,
            ),
        ]
    )

    for key, value in options_dict.items():

        if key == "method":
            current_style = default_style.copy()
            current_style["margin-top"] = "20px"
        else:
            current_style = default_style
        layer_layout.children.append(
            dbc.Row(
                [
                    dbc.InputGroupText(key),
                    dbc.Input(
                        id={"type": f"{key}_input", "index": f"{i}"},
                        value=value,
                        type="text",
                    ),
                ],
                style=current_style,
            )
        )

    # additional setting input for orca block structure

    layer_layout.children.append(
        dbc.Row(
            [
                dbc.Button(
                    "Add additional settings block",
                    id={"type": "add_settings_block", "index": f"{i}"},
                    n_clicks=0,
                    style={"margin-top": "20px"},
                ),
                dbc.Col(
                    [
                        dbc.Row(
                            dbc.InputGroupText("Add settings block"),
                        ),
                        dbc.Row(
                            dbc.Input(
                                value="scf",
                                type="text",
                                id={
                                    "type": "additional_settings_block_input",
                                    "index": f"{i}",
                                    "n_clicks": 0,
                                },
                                style={"width": "100%"},
                            ),
                        ),
                    ],
                    style=default_style,
                    id={"type": "additional_settings_block_col", "index": f"{i}"},
                ),
                dbc.Col(
                    [
                        dbc.Row(
                            dbc.InputGroupText("Additional settings"),
                        ),
                        dbc.Row(
                            [
                                dbc.Input(
                                    value="MAXITER 0",
                                    type="text",
                                    id={
                                        "type": "additional_settings_value_input",
                                        "index": f"{i}",
                                        "n_clicks": 0,
                                    },
                                    style={"width": "100%"},
                                ),
                            ]
                        ),
                    ],
                    style=default_style,
                    id={
                        "type": "additional_settings_value_col",
                        "index": f"{i}",
                    },
                ),
            ],
            style=default_style,
        )
    )

    return layer_layout


def create_config_file(
    n_clicks,
    main_config_inputs,
    structure_check_config_inputs,
    analysis_config_inputs,
    layer_config_inputs,
):
    settings_dict = defaultdict(dict)

    for key, value in main_config_inputs.items():
        if key == "parallel_layer_run":
            settings_dict["main_config"][key] = bool(value)
        if key == "common_input_files":
            settings_dict["main_config"][key] = [
                v.strip() for v in value.split(",") if v.strip() != ""
            ]
        if key == "xyz_path":
            if value is None:
                settings_dict["main_config"][key] = "empty"
            else:
                settings_dict["main_config"][key] = str(Path(value).resolve())
        if key == "input_file_path":
            if value is None:
                settings_dict["main_config"][key] = "empty"
            else:
                settings_dict["main_config"][key] = str(Path(value).resolve())
        else:
            settings_dict["main_config"][key] = value

    for key, value in structure_check_config_inputs.items():
        settings_dict["structure_check_config"][key] = value

    for key, value in analysis_config_inputs.items():
        settings_dict["analysis_config"][key] = value

    layer_names = layer_config_inputs["layer_name"]

    for i, layer_name in enumerate(layer_names):
        settings_dict["loop_config"][layer_name] = {}
        settings_dict["loop_config"][layer_name]["options"] = {}
        for key, value in layer_config_inputs.items():

            if key in ["type", "step_id", "additional_input_files"]:
                settings_dict["loop_config"][layer_name][key] = value[i]

            elif key == "additional_settings_block":
                settings_dict["loop_config"][layer_name]["options"]["args"] = {
                    value["block"][i]: value["value"][i]
                }
            elif key != "additional_settings_block" and key != "layer_name":
                settings_dict["loop_config"][layer_name]["options"][key] = value[i]

    config_check_output = "All seems in order with the config shown below."
    try:
        check_config(settings_dict, skip_file_check=False)
    except Exception as e:
        config_check_output = f"Config check failed with error: {e}"

    return [html.Div("Config file created")], settings_dict, config_check_output


def create_layer_cyto_graph(settings_dict):

    layer_graph = {
        "nodes": [],
        "edges": [],
    }

    for layer_name, layer_settings in settings_dict["loop_config"].items():

        layer_graph["nodes"].append(
            {
                "data": {
                    "id": layer_name,
                    "label": layer_name,
                    "type": layer_settings["type"],
                    "step_id": layer_settings["step_id"],
                    "additional_input_files": layer_settings["additional_input_files"],
                    "options": layer_settings["options"],
                }
            }
        )

    for layer_name, layer_settings in settings_dict["loop_config"].items():
        for layer_name2, layer_settings2 in settings_dict["loop_config"].items():
            if int(layer_settings["step_id"]) == int(layer_settings2["step_id"]) - 1:
                layer_graph["edges"].append(
                    {
                        "data": {
                            "source": layer_name,
                            "target": layer_name2,
                        }
                    }
                )

    return layer_graph


def add_callbacks(app: Dash) -> Dash:
    def check_input_path(
        input_path,
    ):
        input_valid = False
        input_invalid = True

        if input_path:
            input_path = Path(input_path).resolve()
            if input_path.is_file():
                input_valid = True
                input_invalid = False

        return input_valid, input_invalid

    def add_layer_config_rows(
        num_layers: int,
        layer_accordion: list,
    ):

        if num_layers is not None:

            if num_layers == len(layer_accordion):
                pass
            elif num_layers < len(layer_accordion):
                layer_accordion = layer_accordion[:num_layers]

            else:

                for i in range(int(num_layers) - len(layer_accordion)):
                    layer_accordion.append(
                        dbc.AccordionItem(
                            [add_single_layer_config(len(layer_accordion))],
                            title=f"Layer {len(layer_accordion)}",
                        )
                    )

        return layer_accordion

    def add_additional_settings_block(
        n_clicks: int,
        additional_settings_value_col_children,
        additional_settings_block_col_children,
        button_id,
    ):

        index = button_id["index"]
        if n_clicks > 0:
            additional_settings_value_col_children.append(
                dbc.Row(
                    [
                        dbc.Input(
                            placeholder="option value, for example MAXITER 0",
                            type="text",
                            id={
                                "type": "additional_settings_value_input",
                                "index": index,
                                "n_clicks": n_clicks,
                            },
                            style={"width": "100%"},
                        ),
                    ]
                )
            )
            additional_settings_block_col_children.append(
                dbc.Row(
                    dbc.Input(
                        placeholder="option group, for example scf",
                        type="text",
                        id={
                            "type": "additional_settings_block_input",
                            "index": index,
                            "n_clicks": n_clicks,
                        },
                        style={"width": "100%"},
                    ),
                )
            )
        return (
            additional_settings_block_col_children,
            additional_settings_value_col_children,
        )

    def displayTapNodeData(data):
        return json.dumps(data, indent=2)

    def export_json(n_clicks, config_name_input, settings_dict):

        if ".json" not in config_name_input:
            config_name_input += ".json"

        with open(config_name_input, "w") as f:
            json.dump(settings_dict, f)

    app.callback(
        Output("input_path_input", "valid"),
        Output("input_path_input", "invalid"),
        Input("input_path_input", "value"),
        supress_inital_call=True,
    )(check_input_path)

    app.callback(
        Output("layer_accordion", "children"),
        Input("layer_name_input", "value"),
        State("layer_accordion", "children"),
        prevent_initial_call=False,
    )(add_layer_config_rows)

    # callback to add additional settings block for layer config
    app.callback(
        Output({"type": "additional_settings_block_col", "index": MATCH}, "children"),
        Output({"type": "additional_settings_value_col", "index": MATCH}, "children"),
        Input({"type": "add_settings_block", "index": MATCH}, "n_clicks"),
        State({"type": "additional_settings_value_col", "index": MATCH}, "children"),
        State({"type": "additional_settings_block_col", "index": MATCH}, "children"),
        State({"type": "add_settings_block", "index": MATCH}, "id"),
        prevent_initial_call=True,
    )(add_additional_settings_block)

    # callback to create config file
    # the order and structure of this dict will be the same as the config file
    app.callback(
        Output("empty_div", "children"),
        Output("json_view", "data"),
        Output("config_check_output", "value"),
        inputs={
            "n_clicks": Input("create_config_file_button", "n_clicks"),
            "main_config_inputs": {
                "output_dir": State("output_path_input", "value"),
                "input_file_path": State("input_path_input", "value"),
                "input_type": State("input_type_input", "value"),
                "xyz_path": State("xyz_dir_path_input", "value"),
                "continue_previous_run": State("continue_previous_run_input", "value"),
                "parallel_layer_run": State("parallel_layer_run_input", "value"),
                "common_input_files": State("common_input_files_input", "value"),
                "orca_version": State("orca_version_input", "value"),
                "max_n_jobs": State("max_n_jobs_input", "value"),
                "max_run_time": State("max_run_time_input", "value"),
                "max_ram_per_core": State("max_ram_per_core_input", "value"),
                "max_nodes": State("max_nodes_input", "value"),
                "wait_for_results_time": State("wait_for_results_time_input", "value"),
            },
            "structure_check_config_inputs": {
                "run_checks": State("run_checks_input", "value"),
            },
            "analysis_config_inputs": {
                "run_benchmark": State("run_benchmark_input", "value"),
            },
            "layer_config_inputs": {
                "layer_name": State(
                    {"type": "layer_name_input", "index": ALL}, "value"
                ),
                "type": State({"type": "layer_type_input", "index": ALL}, "value"),
                "step_id": State({"type": "step_id_input", "index": ALL}, "value"),
                "additional_input_files": State(
                    {"type": "additional_input_files_input", "index": ALL}, "value"
                ),
                "method": State({"type": "method_input", "index": ALL}, "value"),
                "basisset": State({"type": "basisset_input", "index": ALL}, "value"),
                "additional_settings": State(
                    {"type": "additional_calculation_options_input", "index": ALL},
                    "value",
                ),
                "ram_per_core": State(
                    {"type": "ram_per_core_input", "index": ALL}, "value"
                ),
                "n_cores_per_calculation": State(
                    {"type": "n_cores_per_calculation_input", "index": ALL}, "value"
                ),
                "n_calculation_at_once": State(
                    {"type": "n_calculation_at_once_input", "index": ALL}, "value"
                ),
                "disk_storage": State(
                    {"type": "disk_storage_input", "index": ALL}, "value"
                ),
                "walltime": State(
                    {"type": "max_run_time_input", "index": ALL}, "value"
                ),
                "additional_settings_block": {
                    "value": State(
                        {
                            "type": "additional_settings_value_input",
                            "index": ALL,
                            "n_clicks": ALL,
                        },
                        "value",
                    ),
                    "block": State(
                        {
                            "type": "additional_settings_block_input",
                            "index": ALL,
                            "n_clicks": ALL,
                        },
                        "value",
                    ),
                },
            },
        },
        prevent_initial_call=True,
    )(create_config_file)

    app.callback(
        Output("cytoscape", "elements"),
        Input("json_view", "data"),
        prevent_initial_call=True,
    )(create_layer_cyto_graph)

    app.callback(
        Output("cyto_output", "children"),
        Input("cytoscape", "tapNodeData"),
        prevent_initial_call=True,
    )(displayTapNodeData)

    app.callback(
        Output("download_config_file", "data"),
        Input("export_config_file_button", "n_clicks"),
        State("config_name_input", "value"),
        State("json_view", "data"),
        prevent_initial_call=True,
    )(export_json)
    return app
