from script_maker2000.files import read_config


import logging

script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


def test_read_config(temp_work_dir):
    config = read_config("./script_maker2000/data/example_config.json")
    assert config["main_config"]["max_n_jobs"] == 20

    # now try in temp_directory

    config = read_config(temp_work_dir / "example_config.json")

    # assert logger also working when changing directory
    script_maker_log.info("test1")
    script_maker_error.warning("test2")
    assert len(list((temp_work_dir / "output").glob("*.log"))) == 2
