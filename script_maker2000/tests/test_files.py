from script_maker2000.files import (
    read_config,
    create_working_dir_structure,
    collect_input_files,
    read_mol_input_json,
    automatic_ressource_allocation,
    collect_results_,
)

import copy
import logging
import pathlib
import pytest
import zipfile
import pandas as pd

script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


def test_read_config(test_setup_work_dir):

    config = read_config(test_setup_work_dir / "example_config.json")

    # assert (test_setup_work_dir / config["main_config"]["output_dir"]).exists()

    assert config["main_config"]["max_n_jobs"] == 2000

    with pytest.raises(FileNotFoundError):
        config = read_config(test_setup_work_dir / "example_config3.json")


def test_create_working_dir_structure(test_setup_work_dir):
    main_config = read_config(test_setup_work_dir / "example_config.json")

    # input_location = temp_work_dir / "example_molecules.csv"
    create_working_dir_structure(main_config)

    # check that log files, settings, inputs and dirs are at the correct level
    output_path = pathlib.Path(main_config["main_config"]["output_dir"])

    # expecting 5 files at the top level
    # finished, start_input_files, working, example_config.json, example_molecules.json

    assert len(list(output_path.glob("*"))) == 5
    # check that sub dirs are present
    assert len(list(output_path.glob("*/*"))) == 15
    assert len(list(output_path.glob("*/*/*"))) == 10

    # reset input filenames
    for file in pathlib.Path(test_setup_work_dir / "example_xyz").glob("*.xyz"):
        file.rename(file.parent / file.name.replace("START___", "START_"))

    with pytest.raises(
        FileExistsError, match=r"The directory .* already has subfolders setup\. .*"
    ):
        main_config = read_config(test_setup_work_dir / "example_config4.json")
        create_working_dir_structure(main_config)

    for file in pathlib.Path(test_setup_work_dir / "example_xyz").glob("*.xyz"):
        file.rename(file.parent / file.name.replace("START___", "START_"))

    main_config = read_config(test_setup_work_dir / "example_config5.json")
    output_path = pathlib.Path(main_config["main_config"]["output_dir"])

    create_working_dir_structure(main_config)

    # expecting 5 files at the top level
    # finished, start_input_files, working, example_config.json, example_molecules.json
    assert len(list(output_path.glob("*"))) == 5
    # check that two new sub dirs are present
    assert len(list(output_path.glob("*/*"))) == 15
    assert len(list(output_path.glob("*/*/*"))) == 9

    with pytest.raises(KeyError):
        read_config(test_setup_work_dir / "example_config6.json")


def test_collect_input_files(clean_tmp_dir):

    # create a config that has a dir as input and one that has a single xyz file

    main_config_json = read_config(clean_tmp_dir / "example_config.json")

    main_config_dir = copy.deepcopy(main_config_json)
    main_config_dir["main_config"]["input_file_path"] = str(
        pathlib.Path(main_config_json["main_config"]["input_file_path"]).parents[0]
    )

    main_config_xyz = copy.deepcopy(main_config_dir)
    main_config_xyz["main_config"]["input_file_path"] = str(
        list(
            pathlib.Path(main_config_dir["main_config"]["input_file_path"]).glob(
                "*.xyz"
            )
        )[0]
    )

    # test with json file
    zip_path = collect_input_files(
        main_config_json, clean_tmp_dir / "example_prep", "example_json_config"
    )
    extract_path = clean_tmp_dir / "example_prep_json" / "extracted_test"

    with zipfile.ZipFile(zip_path, "r") as zipf:
        zipf.extractall(path=extract_path)

    assert len(list(extract_path.glob("*"))) == 3
    assert len(list(extract_path.glob("*/*"))) == 11

    # test with dir
    zip_path = collect_input_files(
        main_config_dir, clean_tmp_dir / "example_prep_dir", "example_dir_config"
    )
    extract_path = clean_tmp_dir / "example_prep_dir" / "extracted_test"

    with zipfile.ZipFile(zip_path, "r") as zipf:
        zipf.extractall(path=extract_path)

    assert len(list(extract_path.glob("*"))) == 3
    assert len(list(extract_path.glob("*/*"))) == 11

    # test with single xyz file
    zip_path = collect_input_files(
        main_config_xyz, clean_tmp_dir / "example_prep_xyz", "example_xyz_config"
    )
    extract_path = clean_tmp_dir / "example_prep_xyz" / "extracted_test"

    with zipfile.ZipFile(zip_path, "r") as zipf:
        zipf.extractall(path=extract_path)

    assert len(list(extract_path.glob("*"))) == 3
    assert len(list(extract_path.glob("*/*"))) == 1


def test_collect_input_files_from_dir(clean_tmp_dir):
    # change config to use a directory instead of a tar
    main_config = read_config(clean_tmp_dir / "example_config.json")
    main_config["main_config"]["input_file_path"] = str(
        pathlib.Path(main_config["main_config"]["input_file_path"]).parents[0]
    )

    zip_path = collect_input_files(
        main_config, clean_tmp_dir / "example_prep", "example_xyz_config"
    )
    extract_path = clean_tmp_dir / "example_prep" / "extracted_test"

    with zipfile.ZipFile(zip_path, "r") as zipf:
        zipf.extractall(path=extract_path)

    assert len(list(extract_path.glob("*"))) == 3
    assert len(list(extract_path.glob("*/*"))) == 11

    mol_dict = read_mol_input_json(
        clean_tmp_dir
        / "example_prep"
        / "extracted_test"
        / "monolayer_test_molecules.json"
    )

    for entry in mol_dict.values():
        assert "multiplicity" in entry
        assert "charge" in entry
        assert "path" in entry
        assert "key" in entry


def test_read_mol_input_json(clean_tmp_dir):

    json_path = clean_tmp_dir / "example_xyz" / "example_molecules.json"
    example_mol_dict = read_mol_input_json(json_path)

    assert isinstance(example_mol_dict, dict)

    df = pd.DataFrame(example_mol_dict).T

    assert "path" in df.columns
    assert "key" in df.columns
    assert "multiplicity" in df.columns
    assert "charge" in df.columns


def test_automatic_ressource_allocation(clean_tmp_dir):
    # Define a sample main_config dictionary
    main_config = {
        "main_config": {
            "input_file_path": str(clean_tmp_dir / "example_xyz"),
            "max_n_jobs": 10,
            "max_compute_nodes": 5,
            "max_cores_per_node": 4,
            "max_ram_per_core": 8000,
        },
        "loop_config": {
            "test1": {
                "options": {"automatic_ressource_allocation": "normal"},
                "step_id": 0,
            },
            "test2": {
                "options": {"automatic_ressource_allocation": "large"},
                "step_id": 0,
            },
            "test3": {
                "options": {"automatic_ressource_allocation": "custom"},
                "step_id": 1,
            },
        },
    }

    # Call the function with the sample main_config
    result, _ = automatic_ressource_allocation(main_config)

    # Check that the function modified the main_config as expected
    assert result["loop_config"]["test1"]["options"]["n_cores_per_calculation"] == 4
    assert result["loop_config"]["test1"]["options"]["ram_per_core"] == 4000
    assert result["loop_config"]["test2"]["options"]["n_cores_per_calculation"] == 4
    assert result["loop_config"]["test2"]["options"]["ram_per_core"] == 8000
    assert "n_cores_per_calculation" not in result["loop_config"]["test3"]["options"]
    assert "ram_per_core" not in result["loop_config"]["test3"]["options"]

    main_config = {
        "main_config": {
            "input_file_path": str(
                clean_tmp_dir / "example_xyz"
            ),  # replace with a valid path
            "max_n_jobs": 5,
            "max_compute_nodes": 5,
            "max_cores_per_node": 50,
            "max_ram_per_core": 8000,
        },
        "loop_config": {
            "test1": {
                "options": {"automatic_ressource_allocation": "normal"},
                "step_id": 0,
            },
            "test2": {
                "options": {"automatic_ressource_allocation": "large"},
                "step_id": 0,
            },
            "test3": {
                "options": {"automatic_ressource_allocation": "custom"},
                "step_id": 1,
            },
        },
    }

    # Call the function with the sample main_config
    result, output_dict = automatic_ressource_allocation(main_config)
    assert result["loop_config"]["test1"]["options"]["n_cores_per_calculation"] == 24
    assert result["loop_config"]["test1"]["options"]["ram_per_core"] == 4000
    assert result["loop_config"]["test2"]["options"]["n_cores_per_calculation"] == 24
    assert result["loop_config"]["test2"]["options"]["ram_per_core"] == 8000
    assert "n_cores_per_calculation" not in result["loop_config"]["test3"]["options"]
    assert "ram_per_core" not in result["loop_config"]["test3"]["options"]


def test_collect_results_(clean_tmp_dir):
    # Create a temporary directory for testing
    output_dir = clean_tmp_dir / "output"
    output_dir.mkdir()

    # Create some files and directories inside the output directory
    file1 = output_dir / "file1.txt"
    file1.write_text("This is file 1")
    file2 = output_dir / "file2.txt"
    file2.write_text("This is file 2")
    sub_dir = output_dir / "sub_dir"
    sub_dir.mkdir()
    file3 = sub_dir / "file3.txt"
    file3.write_text("This is file 3")

    # Call the collect_results_ function
    zip_path = collect_results_(output_dir)

    # Check that the zip file is created
    assert zip_path.exists()

    # Extract the contents of the zip file
    extract_path = clean_tmp_dir / "extracted_results"
    with zipfile.ZipFile(zip_path, "r") as zipf:
        zipf.extractall(path=extract_path)

    # Check that the extracted files are the same as the original files
    assert (extract_path / "file1.txt").read_text() == "This is file 1"
    assert (extract_path / "file2.txt").read_text() == "This is file 2"
    assert (extract_path / "sub_dir" / "file3.txt").read_text() == "This is file 3"

    # now test with blacklist filter

    zip_path = collect_results_(output_dir, exclude_patterns=["sub_dir"])
    extract_path = clean_tmp_dir / "extracted_results_1"
    with zipfile.ZipFile(zip_path, "r") as zipf:
        zipf.extractall(path=extract_path)

    assert (extract_path / "file1.txt").read_text() == "This is file 1"
    assert (extract_path / "file2.txt").read_text() == "This is file 2"
    assert (extract_path / "sub_dir" / "file3.txt").exists() is False
