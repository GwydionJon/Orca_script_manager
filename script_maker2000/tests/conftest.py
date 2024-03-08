from tempfile import mkdtemp
import json
import pathlib
import shutil
import copy
import pytest
from pathlib import Path
from script_maker2000.files import read_config, create_working_dir_structure


@pytest.fixture
def temp_work_dir():
    tmp_dir = pathlib.Path(mkdtemp())

    current_path = pathlib.Path(__file__)

    # load example config
    example_config_path = (
        current_path / ".." / ".." / "data" / "example_config_xyz.json"
    ).resolve()

    # copy config to tmp dir
    new_config_path = shutil.copy(example_config_path, tmp_dir)
    with open(new_config_path, "r") as f:
        main_dict = json.load(f)

    main_dict["main_config"]["output_dir"] = "output"

    example_mol_dir = (current_path / ".." / ".." / "data" / "example_xyz").resolve()

    example_xyz = shutil.copytree(str(example_mol_dir), str(tmp_dir / "example_xyz"))
    main_dict["main_config"]["input_file_path"] = str(
        Path(example_xyz) / "example_molecules.csv"
    )

    with open(tmp_dir / "example_config.json", "w") as json_file:
        json.dump(main_dict, json_file)

    # make relativ input test config:

    # make faulty file path
    new_config2 = copy.deepcopy(main_dict)
    new_config2["main_config"]["input_file_path"] = "does_not_exist.csv"
    with open(tmp_dir / "example_config3.json", "w") as json_file:
        json.dump(new_config2, json_file)

    # add new loop step without changing output dir
    new_config3 = copy.deepcopy(main_dict)
    new_config3["loop_config"]["test_config"] = {"type": "test"}
    with open(tmp_dir / "example_config4.json", "w") as json_file:
        json.dump(new_config3, json_file)

    # add new loop step and change output dir
    new_config4 = copy.deepcopy(main_dict)
    new_config4["main_config"]["output_dir"] = "new_output"
    new_config4["loop_config"]["test_config"] = {"type": "test"}
    with open(tmp_dir / "example_config5.json", "w") as json_file:
        json.dump(new_config4, json_file)

    return tmp_dir


@pytest.fixture
def pre_config_tmp_dir():

    # tmp_dir = pathlib.Path(mkdtemp())

    current_path = pathlib.Path(__file__)
    (current_path.parents[0] / "tests_dir").mkdir(exist_ok=True)
    tmp_dir = pathlib.Path(mkdtemp(dir=(current_path.parents[0] / "tests_dir")))

    # load example config
    example_config_path = (
        current_path / ".." / ".." / "data" / "example_config_xyz.json"
    ).resolve()

    # copy config to tmp dir
    new_config_path = shutil.copy(example_config_path, tmp_dir)
    with open(new_config_path, "r") as f:
        main_dict = json.load(f)

    example_mol_dir = (current_path / ".." / ".." / "data" / "example_xyz").resolve()

    example_xyz = shutil.copytree(str(example_mol_dir), str(tmp_dir / "example_xyz"))
    # copy input files to module working space

    main_dict["main_config"]["input_file_path"] = str(
        Path(example_xyz) / "example_molecules.csv"
    )

    with open(tmp_dir / "example_config.json", "w") as json_file:
        json.dump(main_dict, json_file)

    main_config = read_config(tmp_dir / "example_config.json")

    # input_location = temp_work_dir / "example_molecules.csv"
    create_working_dir_structure(main_config)

    shutil.copytree(
        tmp_dir / "example_xyz",
        tmp_dir / "example_xyz_output" / "sp_config" / "input",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("*.csv"),
    )
    return tmp_dir


@pytest.fixture
def clean_tmp_dir():

    # tmp_dir = pathlib.Path(mkdtemp())

    current_path = pathlib.Path(__file__)
    (current_path.parents[0] / "tests_dir").mkdir(exist_ok=True)
    tmp_dir = pathlib.Path(mkdtemp(dir=(current_path.parents[0] / "tests_dir")))

    # load example config
    example_config_path = (
        current_path / ".." / ".." / "data" / "example_config_xyz.json"
    ).resolve()

    # copy config to tmp dir
    new_config_path = shutil.copy(example_config_path, tmp_dir)
    with open(new_config_path, "r") as f:
        main_dict = json.load(f)

    example_mol_dir = (current_path / ".." / ".." / "data" / "example_xyz").resolve()

    example_xyz = shutil.copytree(str(example_mol_dir), str(tmp_dir / "example_xyz"))
    # copy input files to module working space

    main_dict["main_config"]["input_file_path"] = str(
        Path(example_xyz) / "example_molecules.csv"
    )

    with open(tmp_dir / "example_config.json", "w") as json_file:
        json.dump(main_dict, json_file)

    return tmp_dir


@pytest.fixture
def all_job_ids(pre_config_tmp_dir):
    example_dir = pre_config_tmp_dir / "example_xyz"
    file_filst = list(example_dir.glob("*.xyz"))
    return [file.stem.split("START_")[1] for file in file_filst]
