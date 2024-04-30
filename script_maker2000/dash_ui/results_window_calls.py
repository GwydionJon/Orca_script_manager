# import dash_treeview_antd as dta
from pathlib import Path
import json
import pandas as pd
from tempfile import mkdtemp
from collections import defaultdict
import zipfile
import cclib

from script_maker2000.files import (
    read_batch_config_file,
    check_dir_in_batch_config,
    add_dir_to_config,
)
from script_maker2000.analysis import extract_infos_from_results, parse_output_file

new_tmpdir = mkdtemp()


def update_results_folder_select(config_name, config_dict, results_folder_value):

    if config_name is None or config_dict is None:
        return ["running", "finished"], "running", None

    sub_config = config_dict[config_name]

    options = []
    for type_ in ["running", "finished"]:

        options.append({"label": type_, "value": type_, "disabled": True})
        entries_list = sub_config.get(type_, [])

        if len(entries_list) == 0:
            continue
        for entry_dir in entries_list:
            options.append({"label": entry_dir, "value": entry_dir})

    if results_folder_value is None:
        results_folder_value = options[0]["value"]

    elif results_folder_value not in [x["value"] for x in options]:
        results_folder_value = options[0]["value"]

    return options, results_folder_value, None


def update_results_config_(
    n_clicks, remote_local_switch, results_config_value, remote_connection
):
    if remote_local_switch == "local":

        config_dict = read_batch_config_file(mode="dict")

    elif remote_local_switch == "remote":

        script_maker_check = remote_connection.run(
            "command -v script_maker_cli >/dev/null 2>&1 && echo 'The orca script manager is installed. ' ||"
            + " echo 'The orca script manager is not installed. '",
            hide=True,
            timeout=120,
        )

        if "not installed" in script_maker_check.stdout:
            raise ModuleNotFoundError(
                "The orca script manager is not installed. Either install manually or submit a job to install it."
            )
        # return-batch-config
        config_file_remote_str = remote_connection.run(
            "ml devel/python/3.11.4 >/dev/null ;script_maker_cli return-batch-config --as_json",
            hide=True,
            warn=True,
            timeout=120,
        )
        if config_file_remote_str.return_code != 0:
            if "No config file found." in config_file_remote_str.stderr:
                raise FileNotFoundError(
                    "No config file found. Please submit a job to create a config file."
                )
        config_file_remote_str = config_file_remote_str.stdout

        if "No config file found." in config_file_remote_str:
            raise FileNotFoundError(
                "No config file found. Please submit a job to create a config file."
            )
        config_dict = json.loads(config_file_remote_str)

    options = [{"label": x, "value": x} for x in config_dict.keys()]

    if len(options) == 0:
        return ["No files found"], "No files found", None

    if results_config_value is None:
        results_config_value = options[0]["value"]

    elif results_config_value not in [x["value"] for x in options]:
        results_config_value = options[0]["value"]

    return options, results_config_value, config_dict


def get_job_progress_dict_(
    calculation_dir, custom_calc_dir, remote_local_switch, remote_connection
):

    if remote_connection is None:
        return None

    if custom_calc_dir is not None and custom_calc_dir != "":
        calculation_dir = custom_calc_dir

        add_dir_to_config(calculation_dir)

    if calculation_dir in ["running", "finished"]:
        return None

    if remote_local_switch == "local":
        result_location = Path(calculation_dir) / "job_backup.json"

        if not Path(result_location).exists():
            error_message = "Error: The job progress file was not found "
            error_message += f"at the specified location '{result_location}'."

            return {"ERROR": error_message}

    elif remote_local_switch == "remote":
        progress_json = calculation_dir + "/job_backup.json"
        backup_json = Path(new_tmpdir) / "job_backup.json"
        try:
            result_location = remote_connection.get(progress_json, str(backup_json))
            result_location = result_location.local

        except FileNotFoundError:
            error_message = "Error: The job progress file was not found "
            error_message += f"at the specified location '{progress_json}'.\n"

            if "\\" in calculation_dir and remote_local_switch == "remote":
                error_message += (
                    "It seems you have given a windows path to a remote calculation. "
                )
                +"Please use a linux path instead.\n"

            return {"ERROR": error_message}

    with open(result_location, "r") as f:
        job_progress_dict = json.load(f)

    return {calculation_dir: job_progress_dict}


def get_jobs_overview(job_progress_dict):

    if job_progress_dict is None:
        return ""

    calculation_dir, job_progress_dict = list(job_progress_dict.items())[0]

    if calculation_dir == "ERROR":
        return job_progress_dict

    status_dict = defaultdict(lambda: 0)

    for unique_job in job_progress_dict.values():
        current_status = unique_job["_current_status"]
        if current_status == "failed":
            status_dict[unique_job["failed_reason"]] += 1
            continue

        status_dict[current_status] += 1

    output_string = f"Status overivew for {calculation_dir}: \n"

    for status, count in status_dict.items():
        output_string += f" - {status}: {count} jobs\n"

    output_string += f" - Total: {sum(status_dict.values())}\n"
    output_string += f" - Sucess rate: {status_dict['finished'] / sum(status_dict.values()) * 100:.2f}%\n"

    return output_string


def download_results_(
    n_clicks, results_folder_value, target_dir, exclude_pattern_value, remote_connection
):
    """_summary_

    Args:
        n_clicks (_type_): trigger for the fucntion (unused.)
        results_folder_value (str): The remote directory to download.
        target_dir (str): The local directory to download to.
        exclude_pattern_value (str): The pattern to exclude from the zip file. Egs. ".gbw, .log" or even "backup"

    Raises:
        e: _description_

    Returns:
        str: Result message.
    """
    if results_folder_value in ["running", "finished"]:
        return "Choose a specific folder to download"

    if target_dir is None:
        target_dir = Path.cwd()

    result_path = Path(results_folder_value)

    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / (result_path.name + ".zip")
    extraction_dir = target_dir / (target_file.stem.split(".zip")[0] + "_results")

    if check_dir_in_batch_config(target_dir) or check_dir_in_batch_config(
        extraction_dir
    ):
        return_str = "Error: The target directory is in the batch config file."
        return_str += "Please choose another directory or delete the current directory."
        return return_str

    extraction_dir.mkdir(parents=True, exist_ok=True)

    # zip the remote folder

    result = remote_connection.run(
        "ml devel/python/3.11.4 >/dev/null ;script_maker_cli collect-results "
        + f" --results_path {result_path.as_posix()} --exclude_patterns {exclude_pattern_value}",
        hide=True,
        timeout=3600,
    )

    zip_path = result.stdout.split("created at")[-1].strip()

    # download the zip file
    remote_connection.get(zip_path, str(target_file))

    # unzip the file
    try:
        with zipfile.ZipFile(target_file, "r") as zipf:
            zipf.extractall(path=extraction_dir)
    except FileNotFoundError as e:
        faulty_path = str(e).split("No such file or directory: ")[-1].strip()
        faulty_path = faulty_path.replace("'", "")

        windoes_max_file_path = 260
        if windoes_max_file_path < len(faulty_path):
            return_str = (
                f"Error: Can't extract {faulty_path} the path is too long for windows. "
            )

            return_str += "Please choose a shorter path and try again."
            return return_str
        else:
            raise e

    # add the extraction dir to the global batch config
    result = add_dir_to_config(extraction_dir)
    if result == "Already in config.":
        return_str = "The target directory is already in the batch config file."
        return_str += (
            " Please choose another directory or delete the current directory."
        )
        return return_str
    return "Downloaded results to " + str(extraction_dir)


def hide_download_column_when_local(remote_local_switch):
    if remote_local_switch == "local":
        return {"display": "none"}
    return {}


def _get_all_mol_dirs_in_finished_dirs(config_dict, files_filter_value):
    # get all mol dirs in finished dirs
    all_output_dict = defaultdict(lambda: defaultdict(list))

    all_output_dict = {"title": "Calculation Overview:", "key": "all", "children": []}

    for config_key in config_dict.keys():
        finished_dirs = config_dict[config_key]["finished"]

        tree_config_dict = {
            "title": config_key,
            "key": f"config_{config_key}",
            "children": [],
        }

        for finished_dir in finished_dirs:
            finished_dir = Path(finished_dir)
            # find all folders within the raw_results_folder
            for mol_main_dir in finished_dir.glob("**/raw_results/*"):

                mol_main_dict = {
                    "title": mol_main_dir.stem,
                    "key": f"main_{str(mol_main_dir)}",
                    "children": [],
                }

                for mol_sub_dir in mol_main_dir.glob("*"):
                    if "failed" in mol_sub_dir.stem:
                        continue
                    if not (
                        mol_sub_dir / (mol_sub_dir.stem + "_calc_result.json")
                    ).exists():
                        parse_output_file(mol_sub_dir)

                    # check if the file should be skipped
                    # if the user has not entered any files to filter
                    # then skip_file is False
                    # if the user has entered a comma separated list of files to filter
                    # then skip_file is True if the file is in the list
                    if len(files_filter_value) == 0:
                        skip_file = False
                    else:
                        skip_file = True

                        for filter in files_filter_value:
                            if filter in mol_sub_dir.stem:
                                skip_file = False

                    if skip_file:
                        continue

                    mol_main_dict["children"].append(
                        {
                            "title": mol_sub_dir.stem,
                            "key": str(mol_sub_dir),
                            "children": [],
                        }
                    )

                if len(mol_main_dict["children"]) == 0:
                    continue
                tree_config_dict["children"].append(mol_main_dict)

        if len(tree_config_dict["children"]) == 0:
            continue
        all_output_dict["children"].append(tree_config_dict)

    return all_output_dict


def create_results_file_tree(files_filter_value):

    config_dict = read_batch_config_file(mode="dict")

    if files_filter_value is None:
        files_filter_value = []

    # if the user has entered a comma separated list of files to filter
    # split the string and remove any empty strings
    else:
        if "," in files_filter_value:
            if "," == files_filter_value[-1]:
                files_filter_value = files_filter_value[:-1]

            files_filter_value = files_filter_value.split(",")
        else:
            files_filter_value = [files_filter_value]

        for i, value_ in enumerate(files_filter_value.copy()):
            value_ = value_.strip()
            if value_ == "":
                files_filter_value.pop(i)
            else:
                files_filter_value[i] = value_

    raw_tree_dict = _get_all_mol_dirs_in_finished_dirs(config_dict, files_filter_value)

    return raw_tree_dict


def update_table_values(
    tree_dict_selected, table_column_input, energy_unit_select, complete_table_data
):

    selected_data = []
    for selected_entry in tree_dict_selected:
        if selected_entry == "all":
            continue
        if "config_" in selected_entry:
            continue
        if "main_" in selected_entry:
            continue

        selected_data.append(selected_entry)
    print(selected_data)
    print(len(selected_data))
    print("")
    table_data, corrections_list = extract_infos_from_results(selected_data)

    if complete_table_data == {}:  # will be reset when downloading a new file.
        complete_table_data = table_data

    columns_mol_info = [
        {"name": ["Molecular Informations", "Charge"], "id": "charge"},
        {"name": ["Molecular Informations", "Multiplicity"], "id": "mult"},
        {"name": ["Molecular Informations", "Atom Count"], "id": "natom"},
        {"name": ["Molecular Informations", "Basisset count"], "id": "nbasis"},
        {"name": ["Molecular Informations", "Mo count"], "id": "nmo"},
    ]
    columns_calc_info = [
        {"name": ["Calculation Setup", "Package Info"], "id": "metadata_package"},
        {"name": ["Calculation Setup", "Basisset"], "id": "metadata_basisset"},
        {"name": ["Calculation Setup", "Functional"], "id": "metadata_functional"},
        {"name": ["Calculation Setup", "Method"], "id": "metadata_method"},
        {"name": ["Calculation Setup", "keywords"], "id": "metadata_keywords"},
        {"name": ["Calculation Setup", "Opt done"], "id": "optdone"},
    ]
    columns_energies = [
        {"name": ["Energies", "Final SP Energy"], "id": "final_sp_energy"},
        {"name": ["Energies", "Final SCF Energy"], "id": "scfenergies"},
        {"name": ["Energies", "Total Correction"], "id": "total_correction"},
    ]

    for correction_key in corrections_list:
        columns_energies.append(
            {
                "name": ["Energies", correction_key.replace("_", " ").capitalize()],
                "id": correction_key,
            }
        )

    columns_thermo = [
        {"name": ["Thermodynamics", "Enthalpy"], "id": "enthalpy"},
        {"name": ["Thermodynamics", "Entropy"], "id": "entropy"},
        {"name": ["Thermodynamics", "Free Energy"], "id": "freeenergy"},
        {"name": ["Thermodynamics", "ZPVE"], "id": "zpve"},
        {"name": ["Thermodynamics", "Temperature"], "id": "temperature"},
        {"name": ["Thermodynamics", "Imaginary Frequencies"], "id": "imaginary_freq"},
    ]

    columns = [{"name": ["", "Molecule Identifier"], "id": "filename"}]

    if "mol_info" in table_column_input:
        columns.extend(columns_mol_info)
    if "calc_setup" in table_column_input:
        columns.extend(columns_calc_info)
    if "energies" in table_column_input:
        columns.extend(columns_energies)
    if "thermo" in table_column_input:
        columns.extend(columns_thermo)

    table_df = pd.DataFrame(table_data).T

    if energy_unit_select != "eV":
        energy_keys = [
            "final_sp_energy",
            "scfenergies",
            "total_correction",
            "enthalpy",
            "freeenergy",
            "zpve",
        ]
        energy_keys.extend(corrections_list)
        for energy_key in energy_keys:
            if energy_key not in table_df.columns:
                continue

            table_df[energy_key] = table_df[energy_key].apply(
                lambda x: cclib.parser.utils.convertor(x, "eV", energy_unit_select)
            )

    # columns = [{"name": i, "id": i} for i in table_data[0].keys()]

    return table_df.to_dict("records"), columns, complete_table_data


def download_table_data(
    n_clicks,
    table_data,
):
    target_dir = Path.cwd()

    # Create an empty DataFrame
    df = pd.DataFrame(table_data)

    # Save the DataFrame to a CSV file
    df.to_csv("table_data.csv", index=False)
    return "Downloaded table data to " + str(target_dir)
