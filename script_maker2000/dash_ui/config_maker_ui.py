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
    update_predefined_config_select,
    add_predefined_config,
)

from script_maker2000.work_manager import (
    possible_layer_types,
    possible_resource_settings,
)

from script_maker2000.files import (
    read_premade_config,
    main_config_keys,
    structure_check_config_keys,
    analysis_config_keys,
    loop_config_keys,
    options_keys,
)


currently_avaiable_layer_types = ["orca"]
default_style = {"margin": "10px", "width": "100%"}


def create_config_manager_layout(json_path: dict) -> html.Div:

    main_div = html.Div(
        children=[],
    )

    config_accordion = dbc.Row(
        create_config_accordion_from_json(json_path), id="config_accordion_row"
    )
    config_buttons_and_display = create_config_buttons_and_display()
    config_load_row = create_config_load_row()
    acc_column = dbc.Col(
        [
            config_load_row,
            config_accordion,
        ],
        md=4,
        lg=4,
        xl=4,
    )
    json_col = dbc.Col(config_buttons_and_display, md=4, lg=4, xl=4)
    cyto_col = create_cyto_graph_layout()

    new_row = dbc.Row([acc_column, json_col, cyto_col])

    main_div.children.append(new_row)
    return main_div


def create_config_load_row() -> dbc.Row:
    predeined_config_select = dbc.Select(
        id="predefined_config_select",
        options=[],
        style={"margin": "20px", "width": "50%"},
    )

    custom_config_path_input = create_new_intput(
        "Add a custom config path.",
        "",
        id_="custom_config_path_input",
        placeholder="Enter a custom path when your desired path is not shown.",
        debounce=True,
    )

    save_default_config_button = dbc.Button(
        "Add default config",
        id="save_default_config_button",
        n_clicks=0,
        style={"margin": "10px", "width": "95%"},
    )

    toggle_override_config = dbc.RadioButton(
        id="toggle_override_config",
        label="Override existing config",
        value=False,
        style={"margin": "10px", "width": "95%", "vertical-align": "middle"},
    )

    safe_config_text_area = dcc.Textarea(
        id="safe_config_textarea",
        placeholder="Saving default config output will be placed here.",
        style={"width": "100%", "height": "120", "margin": "10px"},
        disabled=True,
    )

    load_config_row = dbc.Row(
        [
            html.H3("Load preconfigured Config"),
            custom_config_path_input,
            predeined_config_select,
            dbc.Row(
                [
                    dbc.Col(save_default_config_button, width=5),
                    dbc.Col(toggle_override_config, width=5),
                ]
            ),
            safe_config_text_area,
        ],
        style={"margin": "10px", "width": "95%"},
    )

    return load_config_row


def create_config_accordion_from_json(json_path: dict) -> dbc.Accordion:

    if isinstance(json_path, dict):
        json_dict = json_path
    else:
        json_path = Path(json_path)

        with open(json_path, "r") as f:
            json_dict = json.load(f)

    # load empty config as backup

    with open(Path(__file__).parents[1] / "data" / "empty_config.json", "r") as f:
        backup_dict = json.load(f)

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
            for key in main_config_keys:
                if key in main_value.keys():
                    new_input = create_new_intput(key, main_value[key], debounce=True)
                    new_accordion_item.children.append(new_input)
                else:
                    new_input = create_new_intput(key, backup_dict[key], debounce=True)
                    new_accordion_item.children.append(new_input)
        if main_key == "structure_check_config":
            for key in structure_check_config_keys:
                if key in main_value.keys():
                    new_input = create_new_intput(key, main_value[key], debounce=True)
                    new_accordion_item.children.append(new_input)
                else:
                    new_input = create_new_intput(key, backup_dict[key], debounce=True)
                    new_accordion_item.children.append(new_input)
        if main_key == "analysis_config":
            for key in analysis_config_keys:
                if key in main_value.keys():
                    new_input = create_new_intput(key, main_value[key], debounce=True)
                    new_accordion_item.children.append(new_input)
                else:
                    new_input = create_new_intput(key, backup_dict[key], debounce=True)
                    new_accordion_item.children.append(new_input)

        if main_key == "loop_config":

            layer_accordion = dbc.Accordion(
                children=[],
                id="layer_accordion",
            )

            for i, (loop_key, loop_value) in enumerate(main_value.items()):
                layer_accordion_item = dbc.AccordionItem(
                    children=add_single_layer_config(
                        i, options_dict={loop_key: loop_value}
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
            html.H3("Config File Preview"),
            html.P(
                "Always check the config file before exporting it, as this will reset the internal config."
            ),
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
    key: str,
    value: str,
    id_=None,
    placeholder=None,
    readonly=False,
    debounce=False,
    keep_list=False,
) -> dbc.Row:

    if id_ is None:
        id_ = f"{key}_input"

    if isinstance(value, str):

        if value == "" or value == "empty":
            value = None
            if key == "output_dir":
                placeholder = (
                    "Dir name where the actual calculation on the server will happen"
                )
            elif key == "input_file_path":
                placeholder = "Path to the molecule json file"

        new_input = dbc.Row(
            children=[
                dbc.InputGroupText(key.replace("_", " ")),
                dbc.Input(
                    id=id_,
                    value=value,
                    type="text",
                    placeholder=placeholder,
                    readonly=readonly,
                    debounce=debounce,
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
        if len(value) == 1 and keep_list is False:
            new_input = create_new_intput(key, value[0])
        else:
            new_input = dbc.Row(
                children=[
                    dbc.InputGroupText(key.replace("_", " ")),
                    dbc.Select(
                        id=id_,
                        options=[{"label": i, "value": i} for i in value],
                        value=value[0],
                    ),
                ],
                style=default_style,
            )

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
    # load empty config as backup

    with open(Path(__file__).parents[1] / "data" / "empty_config.json", "r") as f:
        backup_dict = json.load(f)

    if options_dict is None:
        options_dict = backup_dict["loop_config"]

    # loop_config_keys,
    # options_keys,

    if i is None:
        i = list(options_dict.values())[0]["step_id"]

    layer_layout = []

    new_id = {"type": "layer_name_input", "index": f"{i}"}
    new_input = create_new_intput(
        "Layer Name", list(options_dict.keys())[0], new_id, debounce=True
    )
    layer_layout.append(new_input)

    options_dict_entries = list(options_dict.values())[0]
    # for key, value in options_dict_entries.items():
    for key in loop_config_keys:
        if key in options_dict_entries.keys():
            value = options_dict_entries[key]

        else:
            raise ValueError(f"Key {key} not found in options_dict_entries.")

        if key not in ["options", "type"]:
            new_id = {"type": f"{key}_input", "index": f"{i}"}
            new_input = create_new_intput(key, value, new_id, debounce=True)
            layer_layout.append(new_input)

        elif key == "type":
            new_id = {"type": f"{key}_input", "index": f"{i}"}
            new_input = create_new_intput(
                key,
                possible_layer_types,
                new_id,
                keep_list=True,
            )
            new_input.children[1].value = value
            layer_layout.append(new_input)

        elif key == "options":
            options_dict = value
            for options_key in options_keys:
                if options_key in options_dict.keys():
                    options_value = options_dict[options_key]
                else:
                    raise ValueError(f"Key {options_key} not found in options_dict.")

                if options_key not in ["args", "automatic_ressource_allocation"]:
                    new_id = {"type": f"{options_key}_input", "index": f"{i}"}
                    new_input = create_new_intput(
                        options_key, options_value, new_id, debounce=True
                    )
                    layer_layout.append(new_input)

                if options_key == "automatic_ressource_allocation":
                    new_id = {"type": f"{options_key}_input", "index": f"{i}"}

                    new_input = create_new_intput(
                        options_key, possible_resource_settings, new_id
                    )
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
                        ),
                    )
                    layer_layout.append(
                        dbc.Row(
                            [
                                html.P(
                                    "Enter a block name on the left and the respective values on the right."
                                ),
                                html.Br(),
                                html.P("Seperate multiple values with a space."),
                            ]
                        ),
                    )

                    if args_dict == {}:
                        args_dict["empty"] = "empty"

                    for j, (args_key, args_value) in enumerate(args_dict.items()):
                        if args_key == "" or args_key == "empty":
                            args_key = None
                        if args_value == "" or args_value == "empty":
                            args_value = None

                        layer_layout.append(
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Row(
                                                dbc.InputGroupText(
                                                    "Add settings block "
                                                ),
                                            ),
                                            dbc.Row(
                                                dbc.Input(
                                                    value=args_key,
                                                    placeholder="option group, for example scf",
                                                    type="text",
                                                    id={
                                                        "type": "additional_settings_block_input",
                                                        "index": f"{i}",
                                                        "n_clicks": j,
                                                    },
                                                    style={"width": "100%"},
                                                    debounce=True,
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
                                                        placeholder="option value, for example MAXITER 0",
                                                        id={
                                                            "type": "additional_settings_value_input",
                                                            "index": f"{i}",
                                                            "n_clicks": j,
                                                        },
                                                        style={"width": "100%"},
                                                        debounce=True,
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


def load_predefined_config(selected_config, active_item):

    premade_config_dict = read_premade_config("dict")

    selected_config_dict = premade_config_dict[selected_config]

    new_accordion = create_config_accordion_from_json(selected_config_dict)

    return new_accordion, active_item


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
                "config_name": Input("config_name_input", "value"),
                "input_file_path": Input("input_file_path_input", "value"),
                "output_dir": Input("output_dir_input", "value"),
                "parallel_layer_run": Input("parallel_layer_run_input", "value"),
                "wait_for_results_time": Input("wait_for_results_time_input", "value"),
                "continue_previous_run": Input("continue_previous_run_input", "value"),
                "max_n_jobs": Input("max_n_jobs_input", "value"),
                "max_ram_per_core": Input("max_ram_per_core_input", "value"),
                "max_compute_nodes": Input("max_compute_nodes_input", "value"),
                "max_cores_per_node": Input("max_cores_per_node_input", "value"),
                # "max_nodes": Input("max_nodes_input", "value"),
                "max_run_time": Input("max_run_time_input", "value"),
                "input_type": Input("input_type_input", "value"),
                "orca_version": Input("orca_version_input", "value"),
                "common_input_files": Input("common_input_files_input", "value"),
            },
            "structure_check_config_inputs": {
                "run_checks": Input("run_checks_input", "value"),
            },
            "analysis_config_inputs": {
                "run_benchmark": Input("run_benchmark_input", "value"),
            },
            "layer_config_inputs": {
                "layer_name": Input(
                    {"type": "layer_name_input", "index": ALL}, "value"
                ),
                "type": Input({"type": "type_input", "index": ALL}, "value"),
                "step_id": Input({"type": "step_id_input", "index": ALL}, "value"),
                "additional_input_files": Input(
                    {"type": "additional_input_files_input", "index": ALL}, "value"
                ),
                "method": Input({"type": "method_input", "index": ALL}, "value"),
                "basisset": Input({"type": "basisset_input", "index": ALL}, "value"),
                "additional_settings": Input(
                    {"type": "additional_settings_input", "index": ALL},
                    "value",
                ),
                "automatic_ressource_allocation": Input(
                    {"type": "automatic_ressource_allocation_input", "index": ALL},
                    "value",
                ),
                "ram_per_core": Input(
                    {"type": "ram_per_core_input", "index": ALL}, "value"
                ),
                "n_cores_per_calculation": Input(
                    {"type": "n_cores_per_calculation_input", "index": ALL}, "value"
                ),
                "disk_storage": Input(
                    {"type": "disk_storage_input", "index": ALL}, "value"
                ),
                "walltime": Input({"type": "walltime_input", "index": ALL}, "value"),
                "additional_settings_block": {
                    "value": Input(
                        {
                            "type": "additional_settings_value_input",
                            "index": ALL,
                            "n_clicks": ALL,
                        },
                        "value",
                    ),
                    "block": Input(
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
        Output("config_check_output", "value", allow_duplicate=True),
        Input("export_config_file_button", "n_clicks"),
        State("config_name_input", "value"),
        State("json_view", "data"),
        prevent_initial_call=True,
    )(export_json)

    app.callback(
        Output("config_check_output", "value", allow_duplicate=True),
        inputs={
            "n_clicks": Input("collect_input_files_button", "n_clicks"),
            "settings_dict": State("json_view", "data"),
            "config_name_input": State("config_name_input", "value"),
        },
        prevent_initial_call=True,
    )(_collect_input_files)

    app.callback(
        Output("safe_config_textarea", "value", allow_duplicate=True),
        Output("predefined_config_select", "options", allow_duplicate=True),
        Output("predefined_config_select", "value", allow_duplicate=True),
        Input("save_default_config_button", "n_clicks"),
        State("config_name_input", "value"),
        State("json_view", "data"),
        State("toggle_override_config", "value"),
        State("predefined_config_select", "value"),
        prevent_initial_call=True,
    )(add_predefined_config)

    app.callback(
        Output("predefined_config_select", "options"),
        Output("predefined_config_select", "value"),
        Output("safe_config_textarea", "value"),
        Input("custom_config_path_input", "value"),
    )(update_predefined_config_select)

    app.callback(
        Output("config_accordion_row", "children"),
        Output("accordion", "active_item"),
        Input("predefined_config_select", "value"),
        State("accordion", "active_item"),
        prevent_initial_call=True,
    )(load_predefined_config)

    return app
