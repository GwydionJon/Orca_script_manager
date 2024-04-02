import json
import logging
import pathlib
import shutil
from collections import OrderedDict
import pandas as pd
import tarfile
import os

script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


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
    script_maker_log.info(f"creating subfolders: {sub_dir_names} ")

    for subfolder in sub_dir_names:
        if main_config["main_config"]["continue_previous_run"] is False:

            (output_dir / subfolder / "input").mkdir(parents=True)
            (output_dir / subfolder / "output").mkdir(parents=True)
            (output_dir / subfolder / "finished").mkdir(parents=True)
            (output_dir / subfolder / "failed").mkdir(parents=True)

            # copy template files to sub-folder
            if main_config["loop_config"][str(subfolder)]["type"] == "orca":
                slurm_template_path = (
                    pathlib.Path(__file__).parent / "data/orca_template.sbatch"
                )

                shutil.copy(slurm_template_path, output_dir / subfolder)

    (output_dir / "finished" / "raw_results").mkdir(parents=True)
    (output_dir / "finished" / "results").mkdir(parents=True)

    # move input files and main_settings in output folder
    # save config into working dir
    with open(output_dir / "example_config.json", "w", encoding="utf-8") as json_file:
        json.dump(main_config, json_file)

    # save input csv in output folder

    valid_files, input_df = prepare_xyz_files(input_path)
    script_maker_log.info(valid_files)

    new_input_path = output_dir / "start_input_files"
    new_input_path.mkdir(parents=True, exist_ok=True)
    for file in valid_files:
        script_maker_log.info(file)
        mol_id = file.stem.split("___")[1]
        input_df.loc[input_df["key"] == mol_id, "path"] = file
        shutil.copy(file, new_input_path / file.name)

    new_csv_file = output_dir / "input.csv"
    input_df.to_csv(new_csv_file)

    # copy files to output folder

    return output_dir, new_input_path, new_csv_file


def prepare_xyz_files(input_csv):

    found_files, input_df = _check_input_csv(input_csv)

    new_files = []
    for file in found_files:

        if file.stem.startswith("START_") is False:
            new_file_name = file.parent / ("START___" + file.name)

        elif file.stem.startswith("START___") is True:
            continue
        elif file.stem.startswith("START_") is True:
            new_file_name = file.parent / file.name.replace("START_", "START___")

        else:
            raise ValueError(
                "File name does not match any expected pattern. "
                + "Please rename the file according to the following pattern: START_molIdentifier.xyz"
            )
        new_files.append(file.rename(new_file_name))

    return new_files, input_df


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
            (output_dir / sub_dir).exists()
            and main_config["main_config"]["continue_previous_run"] is False
            and override_continue_job is False
        ):
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
        script_maker_log.info("Skipping config validation.")

    output_dir.mkdir(parents=True, exist_ok=True)

    # check if input file/folder is present
    input_path = pathlib.Path(main_config["main_config"]["input_file_path"])
    # manage relativ input file
    if input_path.is_absolute() is False:
        input_path = pathlib.Path(config_file).parent / input_path

    input_path = input_path.resolve()
    main_config["main_config"]["input_file_path"] = str(input_path)

    # remove previous handlers from logging
    # this is mainly relevant for the tests

    for handler in script_maker_log.handlers:
        script_maker_log.removeHandler(handler)
    for handler in script_maker_error.handlers:
        script_maker_error.removeHandler(handler)

    # add log file to loggers
    file_handler_log = logging.FileHandler(output_dir / "log.log")
    file_handler_failed = logging.FileHandler(output_dir / "failed.log")

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler_log.setFormatter(formatter)
    file_handler_failed.setFormatter(formatter)

    script_maker_log.addHandler(file_handler_log)
    script_maker_error.addHandler(file_handler_failed)

    script_maker_log.setLevel("DEBUG")
    file_handler_failed.setLevel("DEBUG")

    return main_config


def _check_input_csv(input_csv, xyz_dir=None):
    input_df = pd.read_csv(input_csv)
    all_input_files = input_df["path"].values
    file_not_found_list = []
    file_suffix_error_list = []

    found_files = []

    for file in all_input_files:
        if isinstance(file, str):
            file = pathlib.Path(file)

        if file.is_absolute() is False:
            if xyz_dir is None:
                raise FileNotFoundError(
                    "Please provide the full path or the xyz dir name."
                )
            file = list(pathlib.Path(xyz_dir).glob(file))
            if len(file) == 0:
                file_not_found_list.append(file)
            if len(file) > 1:
                raise ValueError(
                    f"Found multiple files for {file}. Please provide the full path."
                )
            file = file[0]

        if not file.exists():
            file_not_found_list.append(file)

        elif file.suffix != ".xyz":
            file_suffix_error_list.append(file)

        else:
            found_files.append(file)

    if len(file_not_found_list) > 0:
        raise FileNotFoundError(
            f"Can't find the following input files: {file_not_found_list}"
        )
    if len(file_suffix_error_list) > 0:
        raise ValueError(
            f"Input files must be in xyz format. The following files are not: {file_suffix_error_list}"
        )

    return found_files, input_df


def collect_input_files(config_path, preparation_dir, config_name=None, tar_name=None):
    """This function collects all input files (xyz, config, csv) and

    Args:
        config_path (str): Path to the config file
        input_csv (str): Path to the input csv file
        xyz_dir (str): Path to the xyz files
    """
    # check if config is valid
    main_config = read_config(config_path, perform_validation=True)

    input_csv = pathlib.Path(main_config["main_config"]["input_file_path"])
    if main_config["main_config"]["xyz_path"]:
        xyz_dir = pathlib.Path(main_config["main_config"]["xyz_path"])
    else:
        xyz_dir = None

    # check if input_csv contains valid file paths
    found_files, input_df = _check_input_csv(input_csv, xyz_dir)

    # replace path in input_df with new path
    for i, file in enumerate(found_files):
        file = pathlib.Path(file)
        if file.is_absolute() is False:
            file_path = str(pathlib.Path(xyz_dir.name) / file.name)
        else:
            file_path = str(file)
        input_df.loc[i, "path"] = file_path

    main_config["main_config"]["input_file_path"] = str(input_csv.name)
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
    new_csv_name = preparation_dir / input_csv.name

    input_df.to_csv(new_csv_name)
    if config_name is None:
        new_config_name = preparation_dir / config_path.name
    else:
        new_config_name = preparation_dir / config_name

    with open(new_config_name, "w", encoding="utf-8") as json_file:
        json.dump(main_config, json_file)

    if tar_name is None:
        tar_path = preparation_dir / "test.tar.gz"
    else:
        if tar_name.endswith(".tar.gz"):
            tar_path = preparation_dir / tar_name
        else:
            tar_name = tar_name + ".tar.gz"

            tar_path = preparation_dir / tar_name

    with tarfile.open(tar_path, "w:gz") as tar:
        for file in found_files:
            tar.add(file, arcname="extracted_xyz/" + pathlib.Path(file).name)
        tar.add(new_csv_name, arcname=new_csv_name.name)
        tar.add(new_config_name, arcname=new_config_name.name)

    tar_path = pathlib.Path(tar_path)

    return tar_path
