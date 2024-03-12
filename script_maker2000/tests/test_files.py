from script_maker2000.files import read_config, create_working_dir_structure

import logging
import pathlib
import pytest

script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


def test_read_config(temp_work_dir):

    config = read_config(temp_work_dir / "example_config.json")

    assert (temp_work_dir / config["main_config"]["output_dir"]).exists()

    assert config["main_config"]["max_n_jobs"] == 20

    # assert logger also working when changing directory
    script_maker_log.info("test1")
    script_maker_error.warning("test2")
    assert len(list((temp_work_dir / "output").glob("*.log"))) == 2

    with pytest.raises(FileNotFoundError):
        config = read_config(temp_work_dir / "example_config3.json")


def test_create_working_dir_structure(temp_work_dir):
    main_config = read_config(temp_work_dir / "example_config.json")

    # input_location = temp_work_dir / "example_molecules.csv"
    create_working_dir_structure(main_config)

    # check that log files, settings, inputs and dirs are at the correct level
    output_path = pathlib.Path(main_config["main_config"]["output_dir"])

    assert len(list(output_path.glob("*"))) == 9
    # check that sub dirs are present
    assert len(list(output_path.glob("*/*"))) == 28

    with pytest.raises(FileExistsError):
        main_config = read_config(temp_work_dir / "example_config4.json")
        create_working_dir_structure(main_config)

    main_config = read_config(temp_work_dir / "example_config5.json")
    output_path = pathlib.Path(main_config["main_config"]["output_dir"])

    create_working_dir_structure(main_config)

    assert len(list(output_path.glob("*"))) == 10
    # check that two new sub dirs are present
    assert len(list(output_path.glob("*/*"))) == 32
