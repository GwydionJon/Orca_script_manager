import json
import logging
import pathlib
import shutil
from collections import OrderedDict, defaultdict
import tarfile
import zipfile
from platformdirs import PlatformDirs
import os
import copy

batchLogger = logging.getLogger("BatchManager")


def create_working_dir_structure(
    main_config: dict,
):
    """
       This function generates the data structure for further calculations.
        a main folder with a folder for crest, optimzation, sp and result sub folders
        as well as the corresponding config files.
        In each of these subfolders will be an input, and an output folder.
        These always contain pairs of molecule files and slurm files.

    Args:
        main_config (dict):The main working folder can be extracted from this config dict

    """

    output_dir = pathlib.Path(main_config["main_config"]["output_dir"])
    input_path = pathlib.Path(main_config["main_config"]["input_file_path"])

    # create desired folder structure
    sub_dir_names = [pathlib.Path(key) for key in main_config["loop_config"]]
    batchLogger.info(f"creating subfolders: {sub_dir_names} ")

    for subfolder in sub_dir_names:
        if main_config["main_config"]["continue_previous_run"] is False:

            (output_dir / "working" / subfolder / "input").mkdir(parents=True)
            (output_dir / "working" / subfolder / "output").mkdir(parents=True)
            (output_dir / "working" / subfolder / "finished").mkdir(parents=True)
            (output_dir / "working" / subfolder / "failed").mkdir(parents=True)

            # copy template files to sub-folder
            if main_config["loop_config"][str(subfolder)]["type"] == "orca":
                slurm_template_path = (
                    pathlib.Path(__file__).parent / "data/orca_template.sbatch"
                )

                shutil.copy(slurm_template_path, output_dir / "working" / subfolder)

    (output_dir / "finished" / "raw_results").mkdir(parents=True)
    (output_dir / "finished" / "results").mkdir(parents=True)

    # move input files and main_settings in output folder
    # save config into working dir

    new_config_name = "config__" + main_config["main_config"]["config_name"] + ".json"

    with open(output_dir / new_config_name, "w", encoding="utf-8") as json_file:
        json.dump(main_config, json_file, indent=4)

    # save input csv in output folder

    job_input = read_mol_input_json(input_path)
    found_files = [pathlib.Path(job_setup["path"]) for job_setup in job_input.values()]

    if len(found_files) < 20:
        batchLogger.info(found_files)
    else:
        batchLogger.info(f"Found {len(found_files)} files.")

    new_input_path = output_dir / "start_input_files"
    new_input_path.mkdir(parents=True, exist_ok=True)
    # for orig_file in found_files:
    for key, entry in job_input.items():
        orig_file = pathlib.Path(entry["path"])
        batchLogger.info(orig_file)
        new_file_path = new_input_path / orig_file.name
        shutil.copy(orig_file, new_file_path)
        job_input[key]["path"] = str(new_file_path)

    new_json_file = output_dir / input_path.name

    with open(new_json_file, "w", encoding="utf-8") as json_file:
        json.dump(job_input, json_file, indent=4)

    # copy files to output folder

    return output_dir, new_input_path, new_json_file


def read_mol_input_json(input_json, skip_file_check=False):

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
                if not pathlib.Path(value).exists():
                    raise FileNotFoundError(f"Can't find file {value}")
                if pathlib.Path(value).suffix != ".xyz":
                    raise ValueError(
                        f"Input files must be in xyz format. The following files are not: {value}"
                    )

            if entry_key == "key":
                if key not in file_path.stem:
                    batchLogger.error(
                        "Key in input file does not match the key in the file name. "
                        + f"Please rename the file according to the following pattern: {key}_cXmX.xyz"
                    )
                    raise ValueError(
                        "Key in input file does not match the key in the file name. "
                        + f"Please rename the file according to the following pattern: {key}_cXmX.xyz"
                    )

            if entry_key == "charge":
                if not isinstance(value, int):
                    batchLogger.error(
                        f"Charge must be an integer. Found {value} of type {type(value)}"
                    )
                    raise ValueError(
                        f"Charge must be an integer. Found {value} of type {type(value)}"
                    )
                if int(value) != charge:
                    batchLogger.error(
                        "Charge in input file does not match the charge in the file name. "
                        + f"Please rename the file according to the following pattern: {key}_cXmX.xyz"
                    )
                    raise ValueError(
                        "Charge in input file does not match the charge in the file name. "
                        + f"Please rename the file according to the following pattern: {key}_cXmX.xyz"
                    )

            if entry_key == "multiplicity":
                if not isinstance(value, int):
                    batchLogger.error(
                        f"Multiplicity must be an integer. Found {value} of type {type(value)}"
                    )
                    raise ValueError(
                        f"Multiplicity must be an integer. Found {value} of type {type(value)}"
                    )
                if int(value) != mul:
                    batchLogger.error(
                        "Multiplicity in input file does not match the multiplicity in the file name. "
                        + f"Please rename the file according to the following pattern: {key}_cXmX.xyz"
                    )
                    raise ValueError(
                        "Multiplicity in input file does not match the multiplicity in the file name. "
                        + f"Please rename the file according to the following pattern: {key}_cXmX.xyz"
                    )

    return mol_input


def check_config(main_config, skip_file_check=False, override_continue_job=False):
    """This function checks the main config for the necessary keys and values."""

    if isinstance(main_config, str):
        with open(main_config, "r", encoding="utf-8") as f:
            main_config = json.load(f)
        main_config = OrderedDict(main_config)

    # check if all keys are present
    _check_config_keys(main_config)

    output_dir = pathlib.Path(main_config["main_config"]["output_dir"])
    sub_dir_names = [pathlib.Path(key) for key in main_config["loop_config"]]
    if len(sub_dir_names) == 0:
        raise ValueError("Can't find loop configs. ?")

    for sub_dir in sub_dir_names:

        if (
            (output_dir / "working" / sub_dir).exists()
            and main_config["main_config"]["continue_previous_run"] is False
            and override_continue_job is False
        ):
            batchLogger.error(
                f"The directory {output_dir} already has subfolders setup. "
                + "If you want to continue a previous run please change the "
                + "'continue_previous_run'-option in the main config"
            )
            raise FileExistsError(
                f"The directory {output_dir} already has subfolders setup. "
                + "If you want to continue a previous run please change the "
                + "'continue_previous_run'-option in the main config"
            )

    is_multilayer = main_config["main_config"]["parallel_layer_run"]

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
        if main_config["main_config"]["input_file_path"] is None:
            raise FileNotFoundError("No input file path provided.")

        input_path = pathlib.Path(main_config["main_config"]["input_file_path"])

        if not input_path.exists():
            raise FileNotFoundError(
                f"Can't find input files under {input_path}."
                + " Please check your file name or provide the necessary files."
            )


def _check_config_keys(main_config):
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
    main_config_keys = [
        "config_name",
        "continue_previous_run",
        "max_n_jobs",
        "max_ram_per_core",
        "max_nodes",
        "output_dir",
        "max_run_time",
        "input_file_path",
        "input_type",
        "parallel_layer_run",
        "orca_version",
        "wait_for_results_time",
        "common_input_files",
        "xyz_path",
    ]
    structure_check_config_keys = ["run_checks"]
    analysis_config_keys = ["run_benchmark"]
    loop_config_keys = ["type", "step_id", "additional_input_files", "options"]
    options_keys = [
        "method",
        "basisset",
        "additional_settings",
        "ram_per_core",
        "n_cores_per_calculation",
        "n_calculation_at_once",
        "disk_storage",
        "walltime",
    ]
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

    for key in ["max_n_jobs", "max_ram_per_core", "max_nodes", "wait_for_results_time"]:
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
    This is a very import setup function as it not only reads and provides the main config,
    it also sets the location for the logging files.

    Args:
        config_file (_type_): _description_
    """

    if not isinstance(config_file, dict):
        with open(config_file, "r", encoding="utf-8") as f:
            main_config = json.load(f)
    else:
        main_config = config_file

    main_config = OrderedDict(main_config)

    input_path = pathlib.Path(main_config["main_config"]["input_file_path"])

    # make relative paths absolute
    if input_path.is_absolute() is False:
        input_path = pathlib.Path(config_file).parent / input_path
        input_path = input_path.resolve()
        main_config["main_config"]["input_file_path"] = str(input_path)

    # check if continue_previous_run is set to True
    if override_continue_job:
        main_config["main_config"]["continue_previous_run"] = override_continue_job

    output_dir = pathlib.Path(main_config["main_config"]["output_dir"])
    # when giving a relativ path resolve it in relation to the config file.
    if output_dir.is_absolute() is False:
        if isinstance(config_file, dict):
            output_dir = os.getcwd() / output_dir
        else:
            output_dir = pathlib.Path(config_file).parent / output_dir

    output_dir = output_dir.resolve()
    main_config["main_config"]["output_dir"] = str(output_dir)

    if perform_validation is True:
        check_config(main_config)
    else:
        batchLogger.info("Skipping config validation.")

    output_dir.mkdir(parents=True, exist_ok=True)

    return main_config


def collect_input_files(config_path, preparation_dir, config_name=None, tar_name=None):
    """This function collects all input files (xyz, config, csv) and puts them into a single tar ball.

    Args:
        config_path (str): Path to the config file
        input_csv (str): Path to the input csv file
        xyz_dir (str): Path to the xyz files
    """
    # check if config is valid
    main_config = read_config(config_path, perform_validation=True)

    input_json = pathlib.Path(main_config["main_config"]["input_file_path"])
    if main_config["main_config"]["xyz_path"]:
        xyz_dir = pathlib.Path(main_config["main_config"]["xyz_path"])
    else:
        xyz_dir = None

    # check if input_csv contains valid file paths
    # found_files, input_df = _check_input_csv(input_csv, xyz_dir)
    mol_input = read_mol_input_json(input_json)
    mol_input_new = copy.deepcopy(mol_input)

    for job_key, job_setup in mol_input.items():
        # replace path in input_df with new path

        file = pathlib.Path(job_setup["path"])
        mol_input_new[job_key]["path"] = "extracted_xyz/" + file.name

    main_config["main_config"]["input_file_path"] = str(input_json.name)
    if xyz_dir is not None:
        main_config["main_config"]["xyz_path"] = str(xyz_dir.name)
    else:
        main_config["main_config"]["xyz_path"] = ""

    main_config["main_config"]["output_dir"] = pathlib.Path(
        main_config["main_config"]["output_dir"]
    ).stem

    preparation_dir = pathlib.Path(preparation_dir)
    preparation_dir.mkdir(parents=True, exist_ok=True)

    # write new input csv and config to preparation dir
    new_molecule_json_name = preparation_dir / input_json.name

    with open(new_molecule_json_name, "w", encoding="utf-8") as json_file:
        json.dump(mol_input_new, json_file, indent=4)

    # rename and save config file
    if config_name is None:
        new_config_name = preparation_dir / config_path.name
    else:
        new_config_name = preparation_dir / config_name

    with open(new_config_name, "w", encoding="utf-8") as json_file:
        json.dump(main_config, json_file, indent=4)

    if tar_name is None:
        tar_path = preparation_dir / "test.tar.gz"
    else:
        if not tar_name.endswith(".tar.gz"):
            tar_name = tar_name + ".tar.gz"

        tar_path = preparation_dir / tar_name

    with tarfile.open(tar_path, "w:gz") as tar:

        tar.add(new_molecule_json_name, arcname=new_molecule_json_name.name)
        tar.add(new_config_name, arcname=new_config_name.name)

        for job_setup in mol_input.values():
            file = pathlib.Path(job_setup["path"])
            tar.add(file, arcname="extracted_xyz/" + pathlib.Path(file).name)

    tar_path = pathlib.Path(tar_path)

    return tar_path


def collect_results_(output_dir, exclude_patterns=None):
    # for some reason zip file is many times faster than tar and significantly smaller
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
            if any([pattern in str(file) for pattern in exclude_patterns]):
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
        removed_keys_per_config_key = []
        # these are finished, running and deleted
        for dir_key in ["running", "finished"]:
            dir_list = dir_values.get(dir_key, [])
            for dir_path in dir_list.copy():

                if not pathlib.Path(dir_path).exists():
                    dict_config[key][dir_key].remove(dir_path)
                    removed_keys_all.append(dir_path)
                    removed_keys_per_config_key.append(dir_path)

        # add removed keys to deleted list
        if len(removed_keys_per_config_key) > 0:
            dict_config[key]["deleted"] = list(
                set(dict_config[key].get("deleted", []) + removed_keys_per_config_key)
            )

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

    batch_config = read_batch_config_file("dict")

    if config_name not in batch_config.keys():
        error_msg = f"Can't find config name {config_name} in the batch config.\n"
        error_msg += "Available config names are:\n"
        error_msg += "\n".join(batch_config.keys())

        raise KeyError(error_msg)

    if new_status not in ["running", "finished", "deleted"]:
        raise ValueError(
            f"New status must be either 'running', 'finished' or 'deleted' but is {new_status}."
        )

    for key, dir_values in batch_config.items():
        for dir_key in ["running", "finished", "deleted"]:
            if str(output_dir) in dir_values.get(dir_key, []):
                batch_config[key][dir_key].remove(str(output_dir))

        if new_status not in batch_config[key].keys():
            batch_config[key][new_status] = [str(output_dir)]
        else:
            batch_config[key][new_status].append(str(output_dir))

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

    batch_config = read_batch_config_file("dict")

    # check if the new output dir is already in the config
    if check_dir_in_batch_config(new_output_dir):
        return "Already in config."

    # check if the output dir exists and has the necessary subfolders/files

    new_output_dir = pathlib.Path(new_output_dir)
    if not new_output_dir.exists():
        raise FileNotFoundError(f"Can't find {new_output_dir}.")

    if not (new_output_dir / "finished").exists():
        raise FileNotFoundError(f"Can't find finished folder in {new_output_dir}.")

    if not (new_output_dir / "finished" / "raw_results").exists():
        raise FileNotFoundError(f"Can't find raw_results folder in {new_output_dir}.")

    skipp_job_backup = False
    # check job backup file only if at least one file is in the raw_results folder
    if len(list((new_output_dir / "finished" / "raw_results").glob("*"))) > 0:
        if not (new_output_dir / "job_backup.json").exists():
            raise FileNotFoundError(f"Can't find job_backup.json in {new_output_dir}.")
    else:
        skipp_job_backup = True

    # find the config file
    config_file_list = list(new_output_dir.glob("config__*.json"))

    if len(config_file_list) == 0:
        raise FileNotFoundError(f"Can't find any config file in {new_output_dir}.")
    if len(config_file_list) > 1:
        raise FileNotFoundError(f"Found multiple config files in {new_output_dir}.")

    config_file = config_file_list[0]

    with open(config_file, "r", encoding="utf-8") as f:
        main_config = json.load(f)

    check_config(main_config, skip_file_check=True, override_continue_job=True)
    # get config name
    config_name = main_config["main_config"]["config_name"]
    # check if job is finished
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

    batch_config.get(config_name, {}).get(batch_status, []).append(str(new_output_dir))
    if config_name not in batch_config.keys():
        batch_config[config_name] = defaultdict(list)
        batch_config[config_name][batch_status].append(str(new_output_dir))

    if batch_status not in batch_config[config_name].keys():
        batch_config[config_name][batch_status] = [str(new_output_dir)]

    batch_config_path = read_batch_config_file("path")
    with open(batch_config_path, "w", encoding="utf-8") as f:
        json.dump(batch_config, f)

    return "added to config."
