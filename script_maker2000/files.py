import json
import logging
import pathlib
import shutil
from collections import OrderedDict
import pandas as pd

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

    # copy input files

    # check that all input files start with START_

    # read input files from csv
    input_df = pd.read_csv(input_path)

    all_input_files = input_df["path"].values
    for file in all_input_files:
        if isinstance(file, str):
            file = pathlib.Path(file)
        if file.stem.startswith("START_") is False:
            raise ValueError(
                f"Input file {file} does not start with 'START_'."
                + " Please make sure all input files start with 'START_'."
            )
    new_input_path = shutil.copytree(
        input_path.parent, output_dir / "start_input_files"
    )

    return output_dir, new_input_path


def move_files(input_path, output_path, copy=True):
    """simple wrapper for moving files and handling certain logic requiremens before doing so. TODO

    Args:
        input_path (str): input path
        output_path (str): output path
        copy (bool): copy (True) or move(False) the file

    """

    if copy:
        return shutil.copy(input_path, output_path)
    else:
        return shutil.move(input_path, output_path)


def check_config(main_config):
    input_path = pathlib.Path(main_config["main_config"]["input_file_path"])

    if not input_path.exists():
        raise FileNotFoundError(
            f"Can't find input files under {input_path}."
            + " Please check your file name or provide the necessary files."
        )

    output_dir = pathlib.Path(main_config["main_config"]["output_dir"])
    sub_dir_names = [pathlib.Path(key) for key in main_config["loop_config"]]
    if len(sub_dir_names) == 0:
        raise ValueError("Can't find loop configs. ?")
    for sub_dir in sub_dir_names:

        if (output_dir / sub_dir).exists() and main_config["main_config"][
            "continue_previous_run"
        ] is False:
            raise FileExistsError(
                f"The directory {output_dir} already has subfolders setup. "
                + "If you want to continue a previous run please change the "
                + "'continue_previous_run'-option in the main config"
            )

    script_maker_log.info("Config seems in order.")


def read_config(config_file, perform_validation=True):
    """
    This is a very import setup function as it not only reads and provides the main config,
    it also sets the location for the logging files.

    Args:
        config_file (_type_): _description_
    """

    with open(config_file, "r", encoding="utf-8") as f:
        main_config = json.load(f)
    main_config = OrderedDict(main_config)

    output_dir = pathlib.Path(main_config["main_config"]["output_dir"])
    # when giving a relativ path resolve it in relation to the config file.
    if output_dir.is_absolute() is False:
        output_dir = pathlib.Path(config_file).parent / output_dir

    output_dir = output_dir.resolve()
    main_config["main_config"]["output_dir"] = str(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # check if input file/folder is present
    input_path = pathlib.Path(main_config["main_config"]["input_file_path"])
    # manage relativ input file
    if input_path.is_absolute() is False:
        input_path = pathlib.Path(config_file).parent / input_path

    input_path = input_path.resolve()
    main_config["main_config"]["input_file_path"] = str(input_path)

    if perform_validation is True:
        check_config(main_config)
    else:
        script_maker_log.info("Skipping config validation.")

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
