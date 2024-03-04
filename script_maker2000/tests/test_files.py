from script_maker2000.files import read_config, create_working_dir_structure

import logging
import pathlib


script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


def test_read_config(temp_work_dir):

    config = read_config(temp_work_dir / "example_config.json")
    assert config["main_config"]["max_n_jobs"] == 20

    # assert logger also working when changing directory
    script_maker_log.info("test1")
    script_maker_error.warning("test2")
    assert len(list((temp_work_dir / "output").glob("*.log"))) == 2


def test_create_working_dir_structure(temp_work_dir):
    main_config = read_config(temp_work_dir / "example_config.json")
    config_location = temp_work_dir / "example_config.json"

    current_path = pathlib.Path(__file__)
    print((current_path / "..").resolve())

    # input_location = temp_work_dir / "example_molecules.csv"
    create_working_dir_structure(main_config, config_location)

    # check that log files, settings, inputs and dirs are at the correct level
    assert len(list((temp_work_dir / "output").glob("*"))) == 9
    # check that sub dirs are present
    assert len(list((temp_work_dir / "output").glob("*/*"))) == 10
