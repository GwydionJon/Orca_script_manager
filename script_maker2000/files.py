import json
import logging
import pathlib

script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


def create_working_dir_structure(main_config: dict):
    """
       This function generates the data structure for further calculations.
        a main folder with a folder for crest, optimzation, sp and result sub folders
        as well as the corresponding config files.
        In each of these subfolders will be an input, and an output folder.
        These always contain pairs of molecule files and slurm files.

    Args:
        main_config (dict):The main working folder can be extracted from this config dict

    Raises:
        NotImplementedError: _description_
    """
    raise NotImplementedError()

    # check if folder is empty, if not raise warning.


def move_files(start, end):
    """simple wrapper for moving files and handling certain logic requiremens before doing so. TODO

    Args:
        start (str): input file
        end (str): output file

    Raises:
        NotImplementedError: _description_
    """
    raise NotImplementedError()


def read_config(config_file):
    """_summary_

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

    return main_config
