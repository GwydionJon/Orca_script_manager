import dash_bootstrap_components as dbc
import dash_renderjson
import dash_cytoscape as cyto
import json
from dash import Dash, html, dcc, Input, Output, State, MATCH, ALL
from pathlib import Path


from script_maker2000.dash_ui.config_maker_calls import (
    check_input_path,
    add_additional_settings_block,
    create_config_file,
    export_json,
    _collect_input_files,
    displayTapNodeData,
)


currently_avaiable_layer_types = ["orca"]
default_style = {"margin": "10px", "width": "100%"}


def create_config_manager_layout(json_path: dict) -> html.Div:

    main_div = html.Div(
        children=[],
    )

    config_accordion = create_config_accordion_from_json(json_path)

    config_buttons_and_display = create_config_buttons_and_display()

    acc_column = dbc.Col(config_accordion, md=4, lg=4, xl=4)
    json_col = dbc.Col(config_buttons_and_display, md=4, lg=4, xl=4)
    cyto_col = create_cyto_graph_layout()

    new_row = dbc.Row([acc_column, json_col, cyto_col])

    main_div.children.append(new_row)
    return main_div


def create_config_accordion_from_json(json_path: dict) -> dbc.Accordion:

    json_path = Path(json_path)

    with open(json_path, "r") as f:
        json_dict = json.load(f)

    accordion = dbc.Accordion(
        children=[],
        style={"width": "90%"},
        id="accordion",
    )
    for main_key, main_value in json_dict.items():

        new_accordion_item = dbc.AccordionItem(
            children=[], title=main_key, id=f"{main_key}_accordion_item"
        )

        if main_key == "main_config":
            new_input = create_new_intput("Config Name", json_path.stem)

            new_accordion_item.children.append(new_input)

        if main_key in ["main_config", "structure_check_config", "analysis_config"]:

            for key, value in main_value.items():
                new_input = create_new_intput(key, value)
                if new_input:
                    new_accordion_item.children.append(new_input)
        elif main_key == "loop_config":
            layer_accordion = dbc.Accordion(
                children=[],
                id="layer_accordion",
            )
            for loop_key, loop_value in main_value.items():
                layer_accordion_item = dbc.AccordionItem(
                    children=add_single_layer_config(
                        options_dict={loop_key: loop_value}
                    ),
                    title=loop_key,
                )
                layer_accordion.children.append(layer_accordion_item)

            new_accordion_item.children.append(add_layer_config_layout(layer_accordion))

        accordion.children.append(new_accordion_item)

    return accordion


def create_config_buttons_and_display() -> dbc.Row:
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

    collect_input_files_button = dbc.Button(
        "Collect Input Files",
        id="collect_input_files_button",
        n_clicks=0,
        style={"margin": "10px", "width": "30%"},
        disabled=True,
    )

    download_object = dcc.Download(id="download_config_file")
    button_row = dbc.Row(
        [
            create_config_file_button,
            export_config_file_button,
            download_object,
            collect_input_files_button,
        ]
    )

    empty_div = html.Div(id="empty_div", children=[])

    json_view = dash_renderjson.DashRenderjson(id="json_view")

    json_Col = dbc.Col(
        [
            button_row,
            dbc.Row(
                dcc.Textarea(
                    id="config_check_output",
                    placeholder="If the config check fails the error will be displayed here.",
                    style={"width": "100%", "height": "130px"},
                    disabled=True,
                )
            ),
            dbc.Row(
                id="json_output",
                children=[json_view],
            ),
            empty_div,
        ]
    )

    return dbc.Row([json_Col])


def create_cyto_graph_layout() -> dbc.Col:

    cyto_col = dbc.Col(
        [
            dbc.Row(
                cyto.Cytoscape(
                    id="cytoscape",
                    layout={"name": "breadthfirst"},
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
    return cyto_col


def create_new_intput(
    key: str, value: str, id_=None, placeholder=None, readonly=False
) -> dbc.Row:

    if id_ is None:
        id_ = f"{key}_input"

    if isinstance(value, str):

        if value == "":
            value = None
            if key == "output_dir":
                placeholder = (
                    "Dir name where the actual calculation on the server will happen"
                )
            elif key == "input_file_path":
                placeholder = "Path to the molecule json file"
            elif key == "xyz_path":
                placeholder = "Path to the xyz dir (optional)"

        new_input = dbc.Row(
            children=[
                dbc.InputGroupText(key.replace("_", " ")),
                dbc.Input(
                    id=id_,
                    value=value,
                    type="text",
                    placeholder=placeholder,
                    readonly=readonly,
                ),
            ],
            style=default_style,
        )
    elif isinstance(value, bool):
        new_input = dbc.Row(
            children=[
                dbc.InputGroupText(key.replace("_", " ")),
                dcc.RadioItems(
                    id=id_,
                    options=[
                        {"label": "True", "value": True},
                        {"label": "False", "value": False},
                    ],
                    value=value,
                ),
            ],
            style=default_style,
        )

    elif isinstance(value, int):
        new_input = dbc.Row(
            children=[
                dbc.InputGroupText(key.replace("_", " ")),
                dbc.Input(
                    id=id_,
                    value=value,
                    type="number",
                ),
            ],
            style=default_style,
        )
    # filter out nested lists if they are only 1 element long
    elif isinstance(value, list):
        if len(value) == 1:
            new_input = create_new_intput(key, value[0])

    else:
        print(f"Type {type(value)} not supported yet. {key, value}")
        return None

    return new_input


def add_layer_config_layout(layer_accordion):

    layer_config_input_group = dbc.Col(
        id="layer_config",
        children=[
            dbc.Row(
                [
                    dbc.InputGroupText("total number of calculation layers"),
                    dbc.Input(
                        id="layer_name_input",
                        value=len(layer_accordion.children),
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
                children=[layer_accordion],
            ),
        ],
    )

    return layer_config_input_group


def add_single_layer_config(i: int = None, options_dict: dict = None):

    if i is None and options_dict is None:
        raise ValueError("Either i or options_dict must be provided.")

    if options_dict is None:
        options_dict = {
            f"sp_config_{i}": {
                "type": "orca",
                "step_id": i,
                "additional_input_files": "",
                "options": {
                    "method": "HF",
                    "basisset": " DEF2-SVP",
                    "additional_settings": "",
                    "ram_per_core": 20,
                    "n_cores_per_calculation": 2,
                    "n_calculation_at_once": 30,
                    "disk_storage": 0,
                    "walltime": "0:2:00",
                    "args": {"scf": ["MAXITER 0"]},
                },
            }
        }

    if i is None:
        i = list(options_dict.values())[0]["step_id"]

    layer_layout = []

    new_id = {"type": "layer_name_input", "index": f"{i}"}
    new_input = create_new_intput("Layer Name", list(options_dict.keys())[0], new_id)
    layer_layout.append(new_input)

    options_dict_entries = list(options_dict.values())[0]
    for key, value in options_dict_entries.items():
        if key != "options":
            new_id = {"type": f"{key}_input", "index": f"{i}"}
            new_input = create_new_intput(key, value, new_id)
            layer_layout.append(new_input)

        elif key == "options":
            options_dict = value
            for options_key, options_value in options_dict.items():

                if options_key != "args":
                    new_id = {"type": f"{options_key}_input", "index": f"{i}"}
                    new_input = create_new_intput(options_key, options_value, new_id)
                    layer_layout.append(new_input)

                elif options_key == "args":
                    args_dict = options_value

                    layer_layout.append(
                        dbc.Row(
                            [
                                dbc.Button(
                                    "Add additional settings block",
                                    id={"type": "add_settings_block", "index": f"{i}"},
                                    n_clicks=0,
                                    style={"margin-top": "20px"},
                                ),
                            ]
                        )
                    )

                    for j, (args_key, args_value) in enumerate(args_dict.items()):
                        layer_layout.append(
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Row(
                                                dbc.InputGroupText(
                                                    "Add settings block"
                                                ),
                                            ),
                                            dbc.Row(
                                                dbc.Input(
                                                    value=args_key,
                                                    type="text",
                                                    id={
                                                        "type": "additional_settings_block_input",
                                                        "index": f"{i}",
                                                        "n_clicks": j,
                                                    },
                                                    style={"width": "100%"},
                                                ),
                                            ),
                                        ],
                                        style=default_style,
                                        id={
                                            "type": "additional_settings_block_col",
                                            "index": f"{i}",
                                        },
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Row(
                                                dbc.InputGroupText(
                                                    "Additional settings"
                                                ),
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Input(
                                                        value=args_value,
                                                        type="text",
                                                        id={
                                                            "type": "additional_settings_value_input",
                                                            "index": f"{i}",
                                                            "n_clicks": j,
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
                                ]
                            )
                        )

    return layer_layout


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
                        add_single_layer_config(len(layer_accordion)),
                        title=f"Layer {len(layer_accordion)}",
                    )
                )

    return layer_accordion


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

    app.callback(
        Output("input_file_path_input", "valid"),
        Output("input_file_path_input", "invalid"),
        Input("input_file_path_input", "value"),
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
        Output("empty_div", "children", allow_duplicate=True),
        Output("json_view", "data"),
        Output("config_check_output", "value", allow_duplicate=True),
        Output("collect_input_files_button", "disabled"),
        inputs={
            "n_clicks": Input("create_config_file_button", "n_clicks"),
            "main_config_inputs": {
                "output_dir": State("output_dir_input", "value"),
                "input_file_path": State("input_file_path_input", "value"),
                "input_type": State("input_type_input", "value"),
                "xyz_path": State("xyz_path_input", "value"),
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
                "type": State({"type": "type_input", "index": ALL}, "value"),
                "step_id": State({"type": "step_id_input", "index": ALL}, "value"),
                "additional_input_files": State(
                    {"type": "additional_input_files_input", "index": ALL}, "value"
                ),
                "method": State({"type": "method_input", "index": ALL}, "value"),
                "basisset": State({"type": "basisset_input", "index": ALL}, "value"),
                "additional_settings": State(
                    {"type": "additional_settings_input", "index": ALL},
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
                "walltime": State({"type": "walltime_input", "index": ALL}, "value"),
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
        State("Config Name_input", "value"),
        State("json_view", "data"),
        prevent_initial_call=True,
    )(export_json)

    app.callback(
        Output("config_check_output", "value", allow_duplicate=True),
        inputs={
            "n_clicks": Input("collect_input_files_button", "n_clicks"),
            "settings_dict": State("json_view", "data"),
            "config_name_input": State("Config Name_input", "value"),
        },
        prevent_initial_call=True,
    )(_collect_input_files)

    return app
