from collections import defaultdict, OrderedDict
import json
from pathlib import Path
import dash_bootstrap_components as dbc
from dash import html
from script_maker2000.files import (
    check_config,
    collect_input_files,
    read_premade_config,
    add_premade_config,
    automatic_ressource_allocation,
)


def create_config_file(
    n_clicks,
    main_config_inputs,
    structure_check_config_inputs,
    analysis_config_inputs,
    layer_config_inputs,
):
    settings_dict = defaultdict(OrderedDict)

    for key, value in main_config_inputs.items():

        if value is None:
            value = "empty"

        if key == "parallel_layer_run":
            settings_dict["main_config"][key] = bool(value)
        elif key == "common_input_files":
            settings_dict["main_config"][key] = [
                v.strip() for v in value.split(",") if v.strip() != ""
            ]
        elif key == "xyz_path":
            if value is None or value == "":
                settings_dict["main_config"][key] = "empty"
            else:
                settings_dict["main_config"][key] = str(Path(value).resolve())
        elif key == "input_file_path":
            if value is None or value == "":
                settings_dict["main_config"][key] = "empty"
            else:
                settings_dict["main_config"][key] = str(Path(value).resolve())
        elif key in [
            "max_n_jobs",
            "max_ram_per_core",
            "max_nodes",
            "wait_for_results_time",
        ]:
            settings_dict["main_config"][key] = int(value)
        else:
            settings_dict["main_config"][key] = value

    for key, value in structure_check_config_inputs.items():
        if value is None:
            value = "empty"
        settings_dict["structure_check_config"][key] = value

    for key, value in analysis_config_inputs.items():
        if value is None:
            value = "empty"
        settings_dict["analysis_config"][key] = value

    layer_names = layer_config_inputs["layer_name"]

    for i, layer_name in enumerate(layer_names):
        check_layer_config(layer_config_inputs, settings_dict, i, layer_name)

    config_check_output = "All seems in order with the config shown below."
    disbale_input_files_button = False

    settings_dict["main_config"]["output_dir"] = "use_current_dir"

    try:
        check_config(settings_dict, skip_file_check=False)
    except Exception as e:
        config_check_output = f"Config check failed with error: {e}"
        config_check_output += "\n\n Input collection disabled."
        disbale_input_files_button = True

    # Automatic ressource allocation

    if disbale_input_files_button is False:
        settings_dict, config_check_output = _perform_resource_check(
            settings_dict, config_check_output
        )

    return (
        [html.Div("Config file created")],
        settings_dict,
        config_check_output,
        disbale_input_files_button,
    )


def _perform_resource_check(settings_dict, config_check_output):
    settings_dict, report_changes_dict = automatic_ressource_allocation(settings_dict)

    if report_changes_dict:
        config_check_output += "\n\nAutomatic ressource allocation was performed. "
        config_check_output += " The following changes were made:\n"
        for key, value in report_changes_dict.items():
            config_check_output += f"{key}: \n"
            for key2, value2 in value.items():
                config_check_output += f"    {key2}: {value2}\n"
    return settings_dict, config_check_output


def check_layer_config(layer_config_inputs, settings_dict, i, layer_name):

    settings_dict["loop_config"][layer_name] = OrderedDict()
    settings_dict["loop_config"][layer_name]["options"] = OrderedDict()

    for key, value in layer_config_inputs.items():

        if isinstance(value, list):
            if value is None or value == [] or value[i] is None:
                value = {i: r"empty"}

        if key in ["type", "step_id", "additional_input_files"]:
            settings_dict["loop_config"][layer_name][key] = value[i]

        elif key == "additional_settings_block":

            if not value["block"] or not value["value"]:
                settings_dict["loop_config"][layer_name]["options"]["args"] = {}
                continue

            if value["block"][i] and value["value"][i]:
                settings_dict["loop_config"][layer_name]["options"]["args"] = {
                    value["block"][i]: value["value"][i]
                }
            else:
                settings_dict["loop_config"][layer_name]["options"]["args"] = {}

        elif key in [
            "ram_per_core",
            "n_cores_per_calculation",
            "n_calculation_at_once",
            "disk_storage",
        ]:
            settings_dict["loop_config"][layer_name]["options"][key] = int(value[i])
        elif key != "additional_settings_block" and key != "layer_name":
            settings_dict["loop_config"][layer_name]["options"][key] = value[i]

        elif key in ["layer_name"]:
            pass

        else:
            raise ValueError(f"Unknown key {key} in layer config.")


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
        elif input_path.is_dir():
            if len(list(input_path.glob("*.xyz"))) > 0:
                input_valid = True
                input_invalid = False

    return input_valid, input_invalid


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
    return json.dumps(OrderedDict(data), indent=2)


def _ordered_dict_recursive(d):
    return OrderedDict(
        (k, _ordered_dict_recursive(v) if isinstance(v, dict) else v)
        for k, v in d.items()
    )


def export_json(n_clicks, config_name_input, settings_dict):

    if settings_dict is None:
        return "Please check the config inputs before exporting."

    if ".json" not in config_name_input:
        config_name_input += ".json"

    with open(config_name_input, "w", encoding="utf-8") as f:
        json.dump(_ordered_dict_recursive(settings_dict), f, indent=4)

    return f"Config file exported as {config_name_input}."


def _collect_input_files(n_clicks, settings_dict, config_name_input):

    try:
        if ".json" not in config_name_input:
            config_json_name = f"{config_name_input}.json"
        else:
            config_json_name = config_name_input
        zip_path = collect_input_files(
            settings_dict,
            config_name_input,
            config_name=config_json_name,
            zip_name=config_name_input,
        )
        output_str = f"Input files collected and tarred at {zip_path}.\n\n"
        output_str += "The tarball will contain all the input files needed for the batch processing.\n"
        output_str += (
            "Please move the tarball to the remote server and extract it there.\n"
        )
        output_str += "To copy the tarball to the remote server you can use the following command:\n"

        output_str += (
            "scp -P <port> <local_file> <remote_user>@<remote_host>:<remote_path>\n"
        )
        output_str += "To start the batch processing on the remote server, run the following command:\n"

        output_str += f"script_maker2000 start_zip -t {zip_path.name}\n"
        output_str += "The zip ball will be automatically extracted and the batch processing will start."

    except Exception as e:
        output_str = f"Error during input collection: {e}"

    return output_str


def update_predefined_config_select(custom_config_path_input):

    config_added_return_text = ""

    selected_config = "empty_config"

    if custom_config_path_input:
        custom_config_path = Path(custom_config_path_input).resolve()
        if custom_config_path.is_file():
            try:
                config_added_return_text, new_config_name = add_premade_config(
                    custom_config_path, return_config_name=True
                )
                selected_config = new_config_name
            except Exception as e:
                config_added_return_text = f"Error adding config: {e}"
                raise e
    new_options = []

    for config in read_premade_config("dict"):
        new_options.append({"label": config, "value": config})

    return new_options, selected_config, config_added_return_text


def add_predefined_config(
    n_clicks,
    config_name_input,
    config_dict,
    toggle_override,
    predefined_select_value,
):

    if config_dict is None:
        new_options = []

        for config in read_premade_config("dict"):
            new_options.append({"label": config, "value": config})
        return (
            "Please check the config inputs before exporting.",
            new_options,
            predefined_select_value,
        )

    return_text = add_premade_config(config_dict, override_config=toggle_override)

    if "already exists" in return_text:
        return_text += (
            " Please enable the override toggle to overwrite the existing config."
        )
        return_value = predefined_select_value
    else:
        return_value = config_name_input

    new_options = []

    for config in read_premade_config("dict"):
        new_options.append({"label": config, "value": config})

    return return_text, new_options, return_value
