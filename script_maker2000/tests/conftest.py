import pytest
from tempfile import mkdtemp
import json
import pathlib
import shutil
import copy


@pytest.fixture
def temp_work_dir():
    tmp_dir = pathlib.Path(mkdtemp())

    current_path = pathlib.Path(__file__)

    # load example config
    example_config_path = (
        current_path / ".." / ".." / "data" / "example_config.json"
    ).resolve()

    # copy config to tmp dir
    new_config_path = shutil.copy(example_config_path, tmp_dir)

    with open(new_config_path, "r") as f:
        main_dict = json.load(f)

    main_dict["main_config"]["output_dir"] = "output"

    example_mol_csv = (
        current_path / ".." / ".." / "data" / "example_molecules.csv"
    ).resolve()

    example_csv = shutil.copy(example_mol_csv, tmp_dir)
    main_dict["main_config"]["input_file_path"] = str(example_csv)

    with open(tmp_dir / "example_config.json", "w") as json_file:
        json.dump(main_dict, json_file)

    # make relativ input test config:
    new_config1 = copy.deepcopy(main_dict)
    new_config1["main_config"]["input_file_path"] = "example_molecules.csv"

    with open(tmp_dir / "example_config2.json", "w") as json_file:
        json.dump(new_config1, json_file)

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
