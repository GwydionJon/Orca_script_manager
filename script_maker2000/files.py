import json
import logging
import pathlib
import shutil


script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


def create_working_dir_structure(main_config: dict, config_path: str):
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

    for subfolder in [
        "force_field",
        "crest",
        "optimization",
        "single_point",
    ]:
        # check if subfolder already exists, if so, this is most likely an already used directory
        if (output_dir / subfolder).exists():
            raise FileExistsError(
                f"The directory {output_dir} already has subfolders setup. "
                + "If you want to continue a previous run please change the "
                + "'continue_previous_run'-option in the main config"
            )
        (output_dir / subfolder / "input").mkdir(parents=True)
        (output_dir / subfolder / "output").mkdir(parents=True)

    (output_dir / "finished" / "raw_results").mkdir(parents=True)
    (output_dir / "finished" / "results").mkdir(parents=True)

    # move input files and main_settings in output folder
    new_config_path = move_files(config_path, output_dir)
    new_input_path = move_files(input_path, output_dir)

    return output_dir, new_config_path, new_input_path


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


def read_config(config_file):
    """This is a very import setup function as it not only reads and provides the main config,
    it also sets the location for the logging files.

    Args:
        config_file (_type_): _description_
    """

    with open(config_file, "r") as f:
        main_config = json.load(f)

    output_dir = pathlib.Path(main_config["main_config"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

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
