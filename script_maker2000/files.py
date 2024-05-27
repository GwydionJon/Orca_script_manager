import json
import logging
import pathlib
import shutil
from collections import OrderedDict, defaultdict
import zipfile
from platformdirs import PlatformDirs
import os
import copy
import re

batchLogger = logging.getLogger("BatchManager")


# config keys
main_config_keys = [
    "config_name",
    "input_file_path",
    "output_dir",
    "parallel_layer_run",
    "wait_for_results_time",
    "continue_previous_run",
    "max_n_jobs",
    "max_ram_per_core",
    "max_compute_nodes",
    "max_cores_per_node",
    "max_run_time",
    "input_type",
    "orca_version",
    "common_input_files",
]
structure_check_config_keys = ["run_checks"]
analysis_config_keys = ["run_benchmark"]
loop_config_keys = ["type", "step_id", "additional_input_files", "options"]
options_keys = [
    "method",
    "basisset",
    "additional_settings",
    "automatic_ressource_allocation",
    "ram_per_core",
    "n_cores_per_calculation",
    "disk_storage",
    "walltime",
    "args",
]


def create_working_dir_structure(
    main_config: dict,
):
    """
    This function generates the data structure for further calculations.
    It creates a main folder with subfolders for crest, optimization, sp, and result.
    Each subfolder contains an input and an output folder.
    These folders store molecule files and slurm files.

    Args:
        main_config (dict): The main configuration dictionary containing the necessary information.

    Returns:
        output_dir (pathlib.Path): The path to the main output directory.
        new_input_path (pathlib.Path): The path to the new input folder.
        new_json_file (pathlib.Path): The path to the new JSON file.

    """

    output_dir = pathlib.Path(main_config["main_config"]["output_dir"])
    input_path = pathlib.Path(main_config["main_config"]["input_file_path"])

    # Create desired folder structure
    sub_dir_names = [pathlib.Path(key) for key in main_config["loop_config"]]
    batchLogger.info(f"Creating subfolders: {sub_dir_names}")

    for subfolder in sub_dir_names:
        if main_config["main_config"]["continue_previous_run"] is False:
            # Create input, output, finished, and failed folders for each subfolder
            (output_dir / "working" / subfolder / "input").mkdir(parents=True)
            (output_dir / "working" / subfolder / "output").mkdir(parents=True)
            (output_dir / "working" / subfolder / "finished").mkdir(parents=True)
            (output_dir / "working" / subfolder / "failed").mkdir(parents=True)

            # Copy template files to sub-folder if the type is "orca"
            if main_config["loop_config"][str(subfolder)]["type"] == "orca":
                slurm_template_path = (
                    pathlib.Path(__file__).parent / "data/orca_template.sbatch"
                )
                shutil.copy(slurm_template_path, output_dir / "working" / subfolder)

    # Create "raw_results" and "results" folders in the "finished" folder
    (output_dir / "finished" / "raw_results").mkdir(parents=True)
    (output_dir / "finished" / "results").mkdir(parents=True)

    # Move input files and main_settings to the output folder
    new_config_name = "config__" + main_config["main_config"]["config_name"] + ".json"
    with open(output_dir / new_config_name, "w", encoding="utf-8") as json_file:
        json.dump(main_config, json_file, indent=4)

    # Save input csv in output folder
    job_input = read_mol_input_json(input_path)
    found_files = [pathlib.Path(job_setup["path"]) for job_setup in job_input.values()]

    if len(found_files) < 20:
        batchLogger.info(found_files)
    else:
        batchLogger.info(f"Found {len(found_files)} files.")

    new_input_path = output_dir / "start_input_files"
    new_input_path.mkdir(parents=True, exist_ok=True)

    for key, entry in job_input.items():
        orig_file = pathlib.Path(entry["path"])
        batchLogger.info(orig_file)
        new_file_path = new_input_path / orig_file.name
        shutil.copy(orig_file, new_file_path)
        job_input[key]["path"] = str(new_file_path)

    new_json_file = output_dir / input_path.name

    with open(new_json_file, "w", encoding="utf-8") as json_file:
        json.dump(job_input, json_file, indent=4)

    return output_dir, new_input_path, new_json_file


def read_mol_input_json(input_json, skip_file_check=False):
    """
    Read the molecule input JSON file and perform consistency checks on the file paths and values.

    Args:
        input_json (str): The path to the molecule input JSON file.
        skip_file_check (bool, optional): Whether to skip the file path and format checks. Defaults to False.

    Returns:
        dict: The molecule input dictionary.

    Raises:
        FileNotFoundError: If a file specified in the JSON does not exist.
        ValueError: If the file format is not XYZ or if the file name
        does not match the specified key, charge, or multiplicity.

    """

    with open(input_json, "r", encoding="utf-8") as f:
        mol_input = json.load(f)
    for key, entry in mol_input.items():
        # check that given values are consistent with filename scheme
        file_path = pathlib.Path(entry["path"])
        # split charge and multiplicity from file name
        charge_mult = file_path.stem.split("__")[-1]
        charge_with_c, mul = charge_mult.split("m")
        charge = charge_with_c.split("c")[1]
        charge = int(charge)
        mul = int(mul)

        if "charge" not in entry.keys():
            entry["charge"] = charge
        if "multiplicity" not in entry.keys():
            entry["multiplicity"] = mul

        if skip_file_check:
            return mol_input

        for entry_key, value in entry.items():

            if entry_key == "path":

                new_path = pathlib.Path(value)

                if not new_path.is_absolute():
                    new_path = input_json.parent / new_path

                if not new_path.exists():
                    raise FileNotFoundError(f"Can't find file {value}")
                if new_path.suffix != ".xyz":
                    raise ValueError(
                        f"Input files must be in xyz format. The following file is not: {value}"
                    )

            if entry_key == "key":
                if key not in file_path.stem:
                    error_message = (
                        f"Key in input file does not match the key in the file name. "
                        f"Please rename the file according to the following pattern: {key}_cXmX.xyz"
                    )
                    batchLogger.error(error_message)
                    raise ValueError(error_message)

            if entry_key == "charge":
                if not isinstance(value, int):
                    error_message = f"Charge must be an integer. Found {value} of type {type(value)}"
                    batchLogger.error(error_message)
                    raise ValueError(error_message)
                if int(value) != charge:
                    error_message = (
                        f"Charge in input file does not match the charge in the file name. "
                        f"Please rename the file according to the following pattern: {key}_cXmX.xyz"
                    )
                    batchLogger.error(error_message)
                    raise ValueError(error_message)

            if entry_key == "multiplicity":
                if not isinstance(value, int):
                    error_message = f"Multiplicity must be an integer. Found {value} of type {type(value)}"
                    batchLogger.error(error_message)
                    raise ValueError(error_message)
                if int(value) != mul:
                    error_message = (
                        f"Multiplicity in input file does not match the multiplicity in the file name. "
                        f"Please rename the file according to the following pattern: {key}_cXmX.xyz"
                    )
                    batchLogger.error(error_message)
                    raise ValueError(error_message)

    return mol_input


def check_config(main_config, skip_file_check=False, override_continue_job=False):
    """
    This function checks the main configuration for the necessary keys and values.

    Args:
        main_config (dict or str): The main configuration dictionary or the path to the configuration file.
        skip_file_check (bool, optional): Whether to skip the file path and format checks. Defaults to False.
        override_continue_job (bool, optional): Whether to override the "continue_previous_run"
        option in the main config. Defaults to False.

    Raises:
        ValueError: If the main configuration is missing required keys or has invalid values.
        FileExistsError: If the output directory already has subfolders setup and "continue_previous_run" is False.

    """

    if isinstance(main_config, str):
        with open(main_config, "r", encoding="utf-8") as f:
            main_config = json.load(f)
        main_config = OrderedDict(main_config)

    # check if all keys are present
    _check_config_keys(main_config)

    if main_config["main_config"]["output_dir"]:

        output_dir = pathlib.Path(main_config["main_config"]["output_dir"])
        sub_dir_names = [pathlib.Path(key) for key in main_config["loop_config"]]
        if len(sub_dir_names) == 0:
            raise ValueError("Can't find loop configs.")

        for sub_dir in sub_dir_names:

            if (
                (output_dir / "working" / sub_dir).exists()
                and main_config["main_config"]["continue_previous_run"] is False
                and override_continue_job is False
            ):
                error_message = (
                    f"The directory {output_dir} already has subfolders setup. "
                    "If you want to continue a previous run please change the "
                    "'continue_previous_run'-option in the main config"
                )
                batchLogger.error(error_message)
                raise FileExistsError(error_message)

    is_multilayer = main_config["main_config"]["parallel_layer_run"]

    # check if layer names are unique
    layer_names = []
    for loop_config in main_config["loop_config"]:
        layer_names.append(loop_config)
    if len(layer_names) != len(set(layer_names)):
        raise ValueError(f"Layer names must be unique but are {layer_names}.")

    step_list = []
    for loop_config in main_config["loop_config"]:
        step_list.append(int(main_config["loop_config"][loop_config]["step_id"]))
    # check if double in step list
    if len(step_list) != len(set(step_list)) and is_multilayer is False:
        raise ValueError(
            "When running without 'parallel_layer_run' mode, the step numbers must be unique."
        )
    for step in step_list:
        if step < 0:
            raise ValueError("Step numbers must be positive.")
        if step != max(step_list):
            if step + 1 not in step_list:
                raise ValueError("The step numbers must be consecutive.")
    if min(step_list) != 0:
        raise ValueError("The first step number must be 0.")

    if skip_file_check is False:

        check_input_files(main_config)


def check_input_files(main_config):
    """
    Check if the input files specified in the main configuration exist and have the correct format.

    Args:
        main_config (dict): The main configuration dictionary.

    Raises:
        FileNotFoundError: If the input file path is not provided or the input files cannot be found.
        ValueError: If the input file is not in JSON format or if no XYZ files are found in the input directory.

    """

    input_file_path = main_config["main_config"]["input_file_path"]

    if input_file_path is None:
        raise FileNotFoundError("No input file path provided.")

    input_path = pathlib.Path(main_config["main_config"]["input_file_path"])
    if not input_path.exists():
        raise FileNotFoundError(
            f"Can't find input files under {input_path}."
            + " Please check your file name or provide the necessary files."
        )

    if input_path.is_file() and input_path.suffix != ".json":
        raise ValueError(f"Input file must be in json format. Found {input_path}.")

    if input_path.is_dir():
        if len(list(input_path.glob("*.xyz"))) == 0:
            raise FileNotFoundError(
                f"Can't find any xyz files under {input_path}."
                + " Please check your file name or provide the necessary files."
            )


def _check_config_keys(main_config):
    """
    Check if the main configuration dictionary contains all the required keys.

    Args:
        main_config (dict): The main configuration dictionary.

    Raises:
        KeyError: If any of the required keys are missing.

    """

    main_keys = [
        "main_config",
        "loop_config",
        "structure_check_config",
        "analysis_config",
    ]
    if not set(main_keys).issubset(main_config.keys()):
        raise KeyError(
            "Main categories are missing. Please provide all the following keys:"
            + f" {set(main_keys) - set(main_config.keys())}"
        )

    # main_config keys

    # check if all keys are present
    if not set(main_config_keys).issubset(main_config["main_config"].keys()):
        raise KeyError(
            "Main config keys are missing. Please provide all the following keys: "
            + f"{set(main_config_keys) - set(main_config['main_config'].keys())}"
        )

    if not set(structure_check_config_keys).issubset(
        main_config["structure_check_config"].keys()
    ):
        raise KeyError(
            "Structure check config keys are missing. Please provide all the following keys:"
            + f" {set(structure_check_config_keys) - set(main_config['structure_check_config'].keys())}"
        )
    if not set(analysis_config_keys).issubset(main_config["analysis_config"].keys()):
        raise KeyError(
            "Analysis config keys are missing. Please provide all the following keys:"
            + f" {set(analysis_config_keys) - set(main_config['analysis_config'].keys())}"
        )

    for key in [
        "max_n_jobs",
        "max_ram_per_core",
        "max_compute_nodes",
        "max_cores_per_node",
        "wait_for_results_time",
    ]:
        if not isinstance(main_config["main_config"][key], int) and not isinstance(
            main_config["main_config"][key], float
        ):
            raise ValueError(
                f"{key} must be an integer or float. Found {main_config['main_config'][key]} of type"
                + f"{type(main_config['main_config'][key])}"
            )

    for loop_config in main_config["loop_config"]:
        if not set(loop_config_keys).issubset(
            main_config["loop_config"][loop_config].keys()
        ):
            raise KeyError(
                "Loop config keys are missing. Please provide all the following keys:"
                + f" {set(loop_config_keys) - set(main_config['loop_config'][loop_config].keys())}"
            )
        if not set(options_keys).issubset(
            main_config["loop_config"][loop_config]["options"].keys()
        ):
            raise KeyError(
                "Options keys are missing. Please provide all the following keys:"
                + f" {set(options_keys) - set(main_config['loop_config'][loop_config]['options'].keys())}"
            )
        for option_key, option_value in main_config["loop_config"][loop_config][
            "options"
        ].items():
            if option_key in [
                "ram_per_core",
                "n_cores_per_calculation",
                "n_calculation_at_once",
                "disk_storage",
            ]:
                if not isinstance(option_value, int):
                    raise ValueError(
                        f"{option_key} must be an integer. Found {option_value} of type {type(option_value)}"
                    )


def read_config(config_file, perform_validation=True, override_continue_job=False):
    """
    Read and provide the main configuration from a file or dictionary.

    Args:
        config_file (str or dict): Path to the configuration file or the configuration dictionary.
        perform_validation (bool, optional): Whether to perform validation on the configuration. Defaults to True.
        override_continue_job (bool, optional): Whether to override the "continue_previous_run"
        option in the main config. Defaults to False.

    Returns:
        dict: The main configuration dictionary.

    Raises:
        FileNotFoundError: If the configuration file cannot be found.
        ValueError: If the configuration file is not in JSON format.
    """

    if not isinstance(config_file, dict):
        with open(config_file, "r", encoding="utf-8") as f:
            main_config = json.load(f)
    else:
        main_config = config_file

    main_config = OrderedDict(main_config)

    input_path = pathlib.Path(main_config["main_config"]["input_file_path"])

    # make relative paths absolute
    if not input_path.is_absolute():
        input_path = pathlib.Path(config_file).parent / input_path
        input_path = input_path.resolve()
        main_config["main_config"]["input_file_path"] = str(input_path)

    # check if continue_previous_run is set to True
    if override_continue_job:
        main_config["main_config"]["continue_previous_run"] = override_continue_job

    output_dir = pathlib.Path(main_config["main_config"]["output_dir"])
    # when giving a relative path, resolve it in relation to the config file.
    if not output_dir.is_absolute():
        if isinstance(config_file, dict):
            output_dir = os.getcwd() / output_dir
        else:
            output_dir = pathlib.Path(config_file).parent / output_dir

    output_dir = output_dir.resolve()
    main_config["main_config"]["output_dir"] = str(output_dir)

    if perform_validation:
        check_config(main_config)
    else:
        batchLogger.info("Skipping config validation.")

    return main_config


def collect_xyz_files_to_dict(xyz_dir):
    """
    Collects all xyz files in a directory and returns them as a dictionary.

    Args:
        xyz_dir (str): Path to the directory containing the xyz files.

    Returns:
        dict: Dictionary with the xyz files, where the keys are the file names without the extension
        and the values are dictionaries containing the file path, key, charge, and multiplicity.

    Raises:
        FileNotFoundError: If the specified directory does not exist.
        ValueError: If a file in the directory does not match the expected pattern.

    """
    xyz_dir = pathlib.Path(xyz_dir)
    if not xyz_dir.exists():
        raise FileNotFoundError(f"Can't find directory {xyz_dir}.")

    mol_dict = {}

    for file in xyz_dir.glob("*.xyz"):
        match = re.search(r"__c([+-]?\d+)m([+-]?\d+)", file.stem)
        if not match:
            raise ValueError(
                f"File {file} does not match the pattern {xyz_dir}__cXmX.xyz"
            )

        charge = int(match.group(1))
        multiplicity = int(match.group(2))

        mol_dict[file.stem] = {
            "path": file,
            "key": file.stem,
            "charge": charge,
            "multiplicity": multiplicity,
        }

    return mol_dict


def replace_empty_with_empty_string(config_dict):
    # recursively replace all "empty" with ""

    for key, value in config_dict.items():
        if value == "empty":
            config_dict[key] = ""

        if isinstance(value, dict):
            replace_empty_with_empty_string(value)


def collect_input_files(config_path, preparation_dir, config_name=None, zip_name=None):
    """
    Collects all input files (xyz, config, csv) and puts them into a single zipball.

    Args:
        config_path (str): Path to the config file.
        preparation_dir (str): Path to the directory where the input files will be prepared.
        config_name (str, optional): Name of the config file. If not provided, the original name will be used.
        Defaults to None.
        zip_name (str, optional): Name of the zipball. If not provided, a default name will be used. Defaults to None.

    Returns:
        pathlib.Path: Path to the created zipball.

    Raises:
        ValueError: If config is given as a dict, but config_name is not provided.
        FileNotFoundError: If no input files are provided.

    """
    # Check if config is valid
    if isinstance(config_path, dict) and config_name is None:
        raise ValueError(
            "If config is given as a dict, the config_name must be provided."
        )

    if config_name:
        if not config_name.endswith(".json"):
            config_name = config_name + ".json"

    main_config = read_config(config_path, perform_validation=True)

    input_path = pathlib.Path(main_config["main_config"]["input_file_path"])

    if not input_path.exists():
        raise FileNotFoundError("No input files provided.")

    if input_path.is_dir():
        # If input path is a directory, collect all xyz files
        mol_input = collect_xyz_files_to_dict(input_path)
        input_json = (
            input_path / f"{main_config['main_config']['config_name']}_molecules.json"
        )
    else:
        # If input path is a file, read the mol_input from the input json file
        input_json = input_path
        mol_input = read_mol_input_json(input_json)

    # Create a deep copy of mol_input to modify the paths
    mol_input_new = copy.deepcopy(mol_input)

    for job_key, job_setup in mol_input.items():
        # Replace path in input_df with new path
        file = pathlib.Path(job_setup["path"])
        mol_input_new[job_key]["path"] = "extracted_xyz/" + file.name

    main_config["main_config"]["input_file_path"] = str(input_json.name)

    main_config["main_config"]["output_dir"] = pathlib.Path(
        main_config["main_config"]["output_dir"]
    ).stem

    # Replace all "empty" with "" in the main config and all sub configs
    replace_empty_with_empty_string(main_config)

    preparation_dir = pathlib.Path(preparation_dir)
    preparation_dir.mkdir(parents=True, exist_ok=True)

    # Write new input json and config to preparation dir
    new_molecule_json_name = preparation_dir / input_json.name

    with open(new_molecule_json_name, "w", encoding="utf-8") as json_file:
        json.dump(mol_input_new, json_file, indent=4)

    # Rename and save config file
    if config_name is None:
        new_config_name = preparation_dir / config_path.name
    else:
        new_config_name = preparation_dir / config_name

    with open(new_config_name, "w", encoding="utf-8") as json_file:
        json.dump(main_config, json_file, indent=4)

    # Create the zip file
    if zip_name is None:
        zip_path = preparation_dir / "test.zip"
    else:
        if not zip_name.endswith(".zip"):
            zip_name = zip_name + ".zip"

        zip_path = preparation_dir / zip_name

    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.write(new_molecule_json_name, arcname=new_molecule_json_name.name)
        zipf.write(new_config_name, arcname=new_config_name.name)

        for job_setup in mol_input.values():
            file = pathlib.Path(job_setup["path"])
            zipf.write(file, arcname="extracted_xyz/" + pathlib.Path(file).name)

    zip_path = pathlib.Path(zip_path)

    return zip_path


def collect_results_(output_dir, exclude_patterns=None):
    # for some reason zip file is many times faster than zip and significantly smaller
    output_dir = pathlib.Path(output_dir)
    if exclude_patterns is None:
        exclude_patterns = []

    if ".zip" not in exclude_patterns:
        exclude_patterns.append(".zip")
    if ".tar" not in exclude_patterns:
        exclude_patterns.append(".tar")
    if ".tar.gz" not in exclude_patterns:
        exclude_patterns.append(".tar.gz")

    zip_path = output_dir / (output_dir.name + ".zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in output_dir.glob("**/*"):

            if "job_backup.json" in str(file):
                zipf.write(file, arcname=str(file.relative_to(output_dir)))

            elif any([pattern in str(file) for pattern in exclude_patterns]):
                continue

            zipf.write(file, arcname=str(file.relative_to(output_dir)))

    return zip_path


def read_batch_config_file(mode):
    """Read the global config file and check if any paths are pointing to non-existing files.

    Args:
        mode (str): path or dict

    Returns:
        str|dict: either the config path or the config dict
    """

    if mode not in ["path", "dict"]:
        raise ValueError(f"Mode must be either 'path' or 'dict' but is {mode}.")

    try:
        user_dirs = PlatformDirs(os.getlogin(), "Orca_Script_Maker")
        user_config_dir = pathlib.Path(user_dirs.user_config_dir)
    except OSError:
        # this should only happen on  github actions
        user_config_dir = pathlib.Path(".")

    user_config_dir.mkdir(parents=True, exist_ok=True)

    config_file = user_config_dir / "available_jobs.json"
    if not config_file.exists():
        print("Can't find config file at", config_file, "creating new one.")
        dict_config = {}

    else:
        with open(config_file, "r", encoding="utf-8") as f:
            dict_config = json.load(f)

    removed_keys_all = []
    # these are the different config keys
    for key, dir_values in dict_config.items():
        # these are finished, running and deleted
        for dir_key in ["running", "finished"]:
            dir_list = dir_values.get(dir_key, [])
            for dir_path in dir_list.copy():

                if not pathlib.Path(dir_path).exists():
                    dict_config[key][dir_key].remove(dir_path)
                    removed_keys_all.append(dir_path)

    if len(removed_keys_all) > 0:
        print(
            "Found outdated paths in globel config, moving these paths to the deleted section:"
        )
        print("Note this will happen when you have removed or changed of files.")
        for dir_ in removed_keys_all:
            print(dir_)
        print("If you want to remove or change these entries open the config at:")
        print(config_file)

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(dict_config, f, indent=4)

    if mode == "path":
        return config_file

    if mode == "dict":
        return dict_config


def change_entry_in_batch_config(config_name, new_status, output_dir):
    """
    Change the status of an entry in the batch config.

    Args:
        config_name (str): Name of the config.
        new_status (str): New status of the entry. Must be either 'running', 'finished', or 'deleted'.
        output_dir (str): Output directory of the entry.

    Returns:
        str: Message indicating that the entry has been changed in the batch config.

    Raises:
        KeyError: If the config name is not found in the batch config.
        ValueError: If the new status is not 'running', 'finished', or 'deleted'.
    """

    batch_config = read_batch_config_file("dict")

    batchLogger.info(
        f"Changing {config_name}  {output_dir} to {new_status}\n"
        + f"Current batch config: {batch_config}"
    )

    if config_name not in batch_config.keys():
        error_msg = f"Can't find config name {config_name} in the batch config.\n"
        error_msg += "Available config names are:\n"
        error_msg += "\n".join(batch_config.keys())

        raise KeyError(error_msg)

    if new_status not in ["running", "finished"]:
        raise ValueError(
            "New status must be either 'running', 'finished' or 'deleted' but is %s."
            % new_status
        )

    for key in ["running", "finished"]:
        dir_values = batch_config[config_name].get(key, [])

        if str(output_dir) in dir_values and key != new_status:
            dir_values.remove(str(output_dir))
            batchLogger.info("Removed %s from %s.", output_dir, key)

        if key == new_status and str(output_dir) not in dir_values:
            dir_values.append(str(output_dir))
            batchLogger.info("Added %s to %s.", output_dir, key)

        batch_config[config_name][key] = dir_values

    batch_config_path = read_batch_config_file("path")
    with open(batch_config_path, "w", encoding="utf-8") as f:
        json.dump(batch_config, f, indent=4)

    return "Changed entry in batch config."


def check_dir_in_batch_config(output_dir):

    batch_config = read_batch_config_file("dict")

    for key, dir_values in batch_config.items():
        for dir_key in ["running", "finished"]:
            for dir_path in dir_values.get(dir_key, []):
                if str(pathlib.Path(output_dir)) == str(pathlib.Path(dir_path)):
                    return "Already in config."

        # if already in deleted remove it from there and add as new
        if output_dir in dir_values.get("deleted", []):
            batch_config[key]["deleted"].remove(output_dir)

    return False


def add_dir_to_config(new_output_dir):
    """
    Add a new output directory to the batch config.

    Args:
        new_output_dir (str): The path to the new output directory.

    Returns:
        str: A message indicating whether the directory was successfully added to the config or not.

    Raises:
        FileNotFoundError: If the new output directory or any required subfolders/files are not found.
    """
    # Convert the new_output_dir to a pathlib.Path object
    new_output_dir = pathlib.Path(new_output_dir)

    # Resolve the absolute path of the new_output_dir
    if not new_output_dir.is_absolute():
        new_output_dir = new_output_dir.resolve()

    # Read the batch config file as a dictionary
    batch_config = read_batch_config_file("dict")

    # Check if the new output dir is already in the config
    if check_dir_in_batch_config(new_output_dir):
        return "Already in config."

    # Check if the output dir exists and has the necessary subfolders/files
    if not new_output_dir.exists():
        raise FileNotFoundError(f"Can't find {new_output_dir}.")

    if not (new_output_dir / "finished").exists():
        raise FileNotFoundError(f"Can't find finished folder in {new_output_dir}.")

    if not (new_output_dir / "finished" / "raw_results").exists():
        raise FileNotFoundError(f"Can't find raw_results folder in {new_output_dir}.")

    skipp_job_backup = False
    # Check job backup file only if at least one file is in the raw_results folder
    if len(list((new_output_dir / "finished" / "raw_results").glob("*"))) > 0:
        if not (new_output_dir / "job_backup.json").exists():
            raise FileNotFoundError(f"Can't find job_backup.json in {new_output_dir}.")
    else:
        skipp_job_backup = True

    # Find the config file
    config_file_list = list(new_output_dir.glob("config__*.json"))

    if len(config_file_list) == 0:
        raise FileNotFoundError(f"Can't find any config file in {new_output_dir}.")
    if len(config_file_list) > 1:
        raise FileNotFoundError(f"Found multiple config files in {new_output_dir}.")

    config_file = config_file_list[0]

    # Read the main config file
    with open(config_file, "r", encoding="utf-8") as f:
        main_config = json.load(f)

    # Check the main config
    check_config(main_config, skip_file_check=True, override_continue_job=True)

    # Get the config name
    config_name = main_config["main_config"]["config_name"]

    # Check if job is finished
    if not skipp_job_backup:
        with open(new_output_dir / "job_backup.json", "r", encoding="utf-8") as f:
            backup_dict = json.load(f)

        status_dict = defaultdict(lambda: 0)
        for unique_job in backup_dict.values():
            current_status = unique_job["_current_status"]
            status_dict[current_status] += 1

        if all(key in {"finished", "failed"} for key in status_dict):
            batch_status = "finished"
        else:
            batch_status = "running"
    else:
        batch_status = "running"

    # Update the batch config with the new output directory
    batch_config.get(config_name, {}).get(batch_status, []).append(str(new_output_dir))
    if config_name not in batch_config.keys():
        batch_config[config_name] = defaultdict(list)
        batch_config[config_name][batch_status].append(str(new_output_dir))

    if batch_status not in batch_config[config_name].keys():
        batch_config[config_name][batch_status] = [str(new_output_dir)]

    # Write the updated batch config to the file
    batch_config_path = read_batch_config_file("path")
    with open(batch_config_path, "w", encoding="utf-8") as f:
        json.dump(batch_config, f, indent=4)

    return "added to config."


def read_premade_config(mode):
    """
    Reads a premade configuration file and returns the configuration data.

    Parameters:
    - mode (str): The mode in which to read the configuration file. Must be one of "path", "dict", or "both".

    Returns:
    - If mode is "path", returns the path to the configuration file.
    - If mode is "dict", returns the configuration data as a dictionary.
    - If mode is "both", returns a tuple containing the path to the configuration file and the configuration data.

    Raises:
    - ValueError: If the mode is not one of "path", "dict", or "both".
    """

    if mode not in ["path", "dict", "both"]:
        raise ValueError(f"Mode must be either 'path', 'dict' or 'both' but is {mode}.")

    try:
        user_dirs = PlatformDirs(os.getlogin(), "Orca_Script_Maker")
        user_config_dir = pathlib.Path(user_dirs.user_config_dir)
    except OSError:
        # this should only happen on  github actions
        user_config_dir = pathlib.Path(".")

    user_config_dir.mkdir(parents=True, exist_ok=True)

    config_file = user_config_dir / "available_configs.json"

    if not config_file.exists():
        print("Can't find config file at", config_file, "creating new one.")
        # read the empty config file

        current_dir = pathlib.Path(__file__).parent
        premade_config_path = current_dir / "data/empty_config.json"

        with open(premade_config_path, "r", encoding="utf-8") as f:
            dict_config = json.load(f)

        dict_config = {"empty_config": dict_config}

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(dict_config, f, indent=4)

    else:
        with open(config_file, "r", encoding="utf-8") as f:
            dict_config = json.load(f)

    if mode == "path":
        return config_file

    if mode == "dict":
        return dict_config

    if mode == "both":
        return config_file, dict_config


def add_premade_config(config_path, return_config_name=False, override_config=False):
    """
    Adds a premade configuration to the existing premade configurations.

    Args:
        config_path (str or dict): The path to the configuration file or
        a dictionary containing the configuration.
        return_config_name (bool, optional): Whether to return the name of the added configuration.
        Defaults to False.
        override_config (bool, optional): Whether to override an existing configuration with the same name.
        Defaults to False.

    Returns:
        str or tuple: If `return_config_name` is True, returns a tuple containing the output
        text and the name of the added configuration.
                      Otherwise, returns the output text as a string.

    Raises:
        FileNotFoundError: If the specified configuration file does not exist.
        JSONDecodeError: If the configuration file is not a valid JSON file.
        KeyError: If the configuration file does not contain the required keys.

    """
    if isinstance(config_path, dict):
        new_config = config_path

    else:
        with open(config_path, "r", encoding="utf-8") as f:
            new_config = json.load(f)

    new_config_name = new_config["main_config"]["config_name"]

    config_file, premade_configs = read_premade_config("both")

    if new_config_name in premade_configs.keys() and override_config is False:
        return_text = f"Config name {new_config_name} already exists. \n"
        return_text += (
            "Please choose a different config name or remove the existing config."
        )
        return return_text

    check_config(new_config, skip_file_check=True)

    premade_configs[new_config_name] = new_config

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(premade_configs, f, indent=4)

    if override_config:
        output_text = f"Overwrote {new_config_name} in premade configs."
    else:
        output_text = f"Added {new_config_name} to premade configs."

    if return_config_name:
        return output_text, new_config_name

    return output_text


def remove_premade_config(config_name):
    """
    Removes a premade config from the list of premade configs.

    Args:
        config_name (str): The name of the config to be removed.

    Returns:
        str: A message indicating whether the config was successfully removed or not.
    """

    config_file, premade_configs = read_premade_config("both")

    if config_name not in premade_configs.keys():
        return f"Can't find config name {config_name} in the premade configs."

    premade_configs.pop(config_name)

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(premade_configs, f, indent=4)

    return f"Removed {config_name} from premade configs."


def automatic_ressource_allocation(main_config):
    """
    Automatically allocates resources for job execution based on the provided main configuration.

    Args:
        main_config (dict): The main configuration containing input file path, loop configuration, and resource limits.

    Returns:
        tuple: A tuple containing the updated main configuration and a dictionary of changes made.

    Raises:
        FileNotFoundError: If the input file path is not found.

    """

    input_file = main_config["main_config"]["input_file_path"]
    input_path = pathlib.Path(input_file)

    if input_path.is_dir():
        job_input = collect_xyz_files_to_dict(input_path)
    elif input_path.is_file():
        job_input = read_mol_input_json(input_path)
    else:
        raise FileNotFoundError(f"Test Can't find input files under {input_path}.")

    # find max parallel layers

    parallel_layer_dict = defaultdict(lambda: 0)
    for loop_key, loop_config in main_config["loop_config"].items():
        parallel_layer_dict[loop_config["step_id"]] += 1

    max_parallel_layers = max(parallel_layer_dict.values())

    potential_n_jobs = len(job_input) * max_parallel_layers
    max_n_jobs = int(main_config["main_config"]["max_n_jobs"])

    if potential_n_jobs > max_n_jobs:
        active_jobs = max_n_jobs
    else:
        active_jobs = potential_n_jobs

    max_compute_nodes = int(main_config["main_config"]["max_compute_nodes"])
    max_cores_per_node = int(main_config["main_config"]["max_cores_per_node"])

    active_jobs_per_node = active_jobs // max_compute_nodes
    if active_jobs_per_node <= 2:
        n_cores_per_calc = 24
    elif active_jobs_per_node <= 4:
        n_cores_per_calc = 12
    elif active_jobs_per_node <= 8:
        n_cores_per_calc = 6
    elif active_jobs_per_node <= 12:
        n_cores_per_calc = 4
    elif active_jobs_per_node <= 24:
        n_cores_per_calc = 2
    else:
        n_cores_per_calc = 1

    if n_cores_per_calc > max_cores_per_node:
        n_cores_per_calc = max_cores_per_node

    max_ram_per_core = int(main_config["main_config"]["max_ram_per_core"])
    # now iterate over the loop_config and set the values

    report_changes_dict = {}

    for loop_key, loop_config in main_config["loop_config"].items():

        if loop_config["options"]["automatic_ressource_allocation"] == "custom":
            continue

        loop_config["options"]["n_cores_per_calculation"] = n_cores_per_calc

        if loop_config["options"]["automatic_ressource_allocation"] == "normal":
            allocated_ram = 4000
        if loop_config["options"]["automatic_ressource_allocation"] == "large":
            allocated_ram = 8000

        if allocated_ram > max_ram_per_core:
            allocated_ram = max_ram_per_core

        report_changes_dict[loop_key] = {
            "n_cores": n_cores_per_calc,
            "ram": allocated_ram,
        }

        loop_config["options"]["ram_per_core"] = allocated_ram

    return main_config, report_changes_dict
