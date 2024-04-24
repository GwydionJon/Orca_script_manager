from collections import defaultdict
import json
from pathlib import Path
import dash_bootstrap_components as dbc
from dash import html
from script_maker2000.files import check_config, collect_input_files


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
        elif key == "common_input_files":
            settings_dict["main_config"][key] = [
                v.strip() for v in value.split(",") if v.strip() != ""
            ]
        elif key == "xyz_path":
            if value is None:
                settings_dict["main_config"][key] = "empty"
            else:
                settings_dict["main_config"][key] = str(Path(value).resolve())
        elif key == "input_file_path":
            if value is None:
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
        settings_dict["structure_check_config"][key] = value

    for key, value in analysis_config_inputs.items():
        settings_dict["analysis_config"][key] = value

    layer_names = layer_config_inputs["layer_name"]

    for i, layer_name in enumerate(layer_names):
        check_layer_config(layer_config_inputs, settings_dict, i, layer_name)

    config_check_output = "All seems in order with the config shown below."
    disbale_input_files_button = False
    try:
        check_config(settings_dict, skip_file_check=False)
    except Exception as e:
        config_check_output = f"Config check failed with error: {e}"
        config_check_output += "\n\n Input collection disabled."
        disbale_input_files_button = True
    return (
        [html.Div("Config file created")],
        settings_dict,
        config_check_output,
        disbale_input_files_button,
    )


def check_layer_config(layer_config_inputs, settings_dict, i, layer_name):
    settings_dict["loop_config"][layer_name] = {}
    settings_dict["loop_config"][layer_name]["options"] = {}
    for key, value in layer_config_inputs.items():
        if key in ["type", "step_id", "additional_input_files"]:
            settings_dict["loop_config"][layer_name][key] = value[i]

        elif key == "additional_settings_block":
            settings_dict["loop_config"][layer_name]["options"]["args"] = {
                value["block"][i]: value["value"][i]
            }

        elif key in [
            "ram_per_core",
            "n_cores_per_calculation",
            "n_calculation_at_once",
            "disk_storage",
        ]:
            settings_dict["loop_config"][layer_name]["options"][key] = int(value[i])
        elif key != "additional_settings_block" and key != "layer_name":
            settings_dict["loop_config"][layer_name]["options"][key] = value[i]


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
    return json.dumps(data, indent=2)


def export_json(n_clicks, config_name_input, settings_dict):

    if ".json" not in config_name_input:
        config_name_input += ".json"

    with open(config_name_input, "w", encoding="utf-8") as f:
        json.dump(settings_dict, f)


def _collect_input_files(n_clicks, settings_dict, config_name_input):

    try:
        if ".json" not in config_name_input:
            config_json_name = f"{config_name_input}.json"
        else:
            config_json_name = config_name_input
        tar_path = collect_input_files(
            settings_dict,
            config_name_input,
            config_name=config_json_name,
            tar_name=config_name_input,
        )
        output_str = f"Input files collected and tarred at {tar_path}.\n\n"
        output_str += "The tarball will contain all the input files needed for the batch processing.\n"
        output_str += (
            "Please move the tarball to the remote server and extract it there.\n"
        )
        output_str += "To copy the tarball to the remote server you can use the following command:\n"

        output_str += (
            "scp -P <port> <local_file> <remote_user>@<remote_host>:<remote_path>\n"
        )
        output_str += "To start the batch processing on the remote server, run the following command:\n"

        output_str += f"script_maker2000 start_tar -t {tar_path.name}\n"
        output_str += "The tar ball will be automatically extracted and the batch processing will start."

    except Exception as e:
        output_str = f"Error during input collection: {e}"

    return output_str
