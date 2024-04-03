from tempfile import mkdtemp
import json
import pathlib
import shutil
import copy
import pytest
from pathlib import Path
import pandas as pd
from script_maker2000.files import read_config, create_working_dir_structure
from script_maker2000.batch_manager import BatchManager


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

    # change xyz file locations in .csv
    df = pd.read_csv(tmp_dir / "example_xyz" / "example_molecules.csv")
    df["path"] = [
        path.resolve() for path in list((tmp_dir / "example_xyz").glob("*.xyz"))
    ]

    df.to_csv(tmp_dir / "example_xyz" / "example_molecules.csv", index=False)

    main_dict["main_config"]["input_file_path"] = str(
        Path(example_xyz) / "example_molecules.csv"
    )

    with open(tmp_dir / "example_config.json", "w") as json_file:
        json.dump(main_dict, json_file)

    return tmp_dir


@pytest.fixture
def test_setup_work_dir(clean_tmp_dir):

    tmp_dir = clean_tmp_dir
    new_config_path = tmp_dir / "example_config.json"
    with open(new_config_path, "r") as f:
        main_dict = json.load(f)

    # make faulty file path
    new_config2 = copy.deepcopy(main_dict)
    new_config2["main_config"]["input_file_path"] = "does_not_exist.csv"
    with open(tmp_dir / "example_config3.json", "w") as json_file:
        json.dump(new_config2, json_file)

    # add new loop step without changing output dir
    new_config3 = copy.deepcopy(main_dict)
    new_config3["loop_config"]["opt_config"]["type"] = "test"
    new_config3["loop_config"]["opt_config"]["step_id"] = 0
    with open(tmp_dir / "example_config4.json", "w") as json_file:
        json.dump(new_config3, json_file)

    # add new loop step and change output dir
    new_config4 = copy.deepcopy(main_dict)
    new_config4["main_config"]["output_dir"] = "new_output"
    new_config4["loop_config"]["sp_config"]["type"] = "test"
    new_config4["loop_config"]["sp_config"]["step_id"] = 1

    with open(tmp_dir / "example_config5.json", "w") as json_file:
        json.dump(new_config4, json_file)

    new_config5 = copy.deepcopy(main_dict)
    new_config5["main_config"]["output_dir"] = "new_output2"
    new_config5["loop_config"]["sp2_config"] = {}
    new_config5["loop_config"]["sp2_config"]["step_id"] = 1
    with open(tmp_dir / "example_config6.json", "w") as json_file:
        json.dump(new_config5, json_file)

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

    main_dict["main_config"]["input_file_path"] = str(
        Path(example_xyz) / "example_molecules.csv"
    )

    # change xyz file locations in .csv
    df = pd.read_csv(tmp_dir / "example_xyz" / "example_molecules.csv")
    df["path"] = [
        path.resolve() for path in list((tmp_dir / "example_xyz").glob("*.xyz"))
    ]
    df.to_csv(tmp_dir / "example_xyz" / "example_molecules.csv", index=False)

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
def multilayer_tmp_dir():
    # tmp_dir = pathlib.Path(mkdtemp())

    current_path = pathlib.Path(__file__)
    (current_path.parents[0] / "tests_dir").mkdir(exist_ok=True)
    tmp_dir = pathlib.Path(mkdtemp(dir=(current_path.parents[0] / "tests_dir")))

    # load example config
    example_config_path = (
        current_path / ".." / ".." / "data" / "example_config_xyz_multilayer.json"
    ).resolve()

    # copy config to tmp dir
    new_config_path = shutil.copy(example_config_path, tmp_dir)
    with open(new_config_path, "r") as f:
        main_dict = json.load(f)

    example_mol_dir = (current_path / ".." / ".." / "data" / "example_xyz").resolve()

    example_xyz = shutil.copytree(str(example_mol_dir), str(tmp_dir / "example_xyz"))
    # copy input files to module working space

    # change xyz file locations in .csv
    df = pd.read_csv(tmp_dir / "example_xyz" / "example_molecules.csv")
    df["path"] = [
        path.resolve() for path in list((tmp_dir / "example_xyz").glob("*.xyz"))
    ]
    df.to_csv(tmp_dir / "example_xyz" / "example_molecules.csv", index=False)

    main_dict["main_config"]["input_file_path"] = str(
        Path(example_xyz) / "example_molecules.csv"
    )

    with open(tmp_dir / "example_config.json", "w") as json_file:
        json.dump(main_dict, json_file)

    return tmp_dir


@pytest.fixture
def pre_started_dir(multilayer_tmp_dir):

    current_path = Path(__file__).parents[0]
    shutil.copy(current_path / "test_data" / "output.tar.gz", multilayer_tmp_dir)
    shutil.unpack_archive(multilayer_tmp_dir / "output.tar.gz", multilayer_tmp_dir)

    # src_dirs
    src_dirs = [
        multilayer_tmp_dir / "output" / "sp_config1",
        multilayer_tmp_dir / "output" / "sp_config2",
        multilayer_tmp_dir / "output" / "opt_config1",
        multilayer_tmp_dir / "output" / "opt_config2",
    ]

    for dir in src_dirs:
        shutil.move(dir, multilayer_tmp_dir / "output" / "working" / dir.stem)

    with open(multilayer_tmp_dir / "output" / "job_backup.json", "r") as f:
        job_backup = json.load(f)

    for key in job_backup.keys():
        job_backup[key]["efficiency_data"] = {}

    with open(multilayer_tmp_dir / "output" / "job_backup.json", "w") as f:
        json.dump(job_backup, f)

    return multilayer_tmp_dir


@pytest.fixture
def job_dict(clean_tmp_dir):
    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)
    return batch_manager.job_dict


@pytest.fixture
def all_job_ids(pre_config_tmp_dir):
    example_dir = pre_config_tmp_dir / "example_xyz"
    file_filst = list(example_dir.glob("*.xyz"))
    return [file.stem.split("START___")[1] for file in file_filst]


@pytest.fixture
def expected_df_only_failed_jobs():
    expected_df_only_failed_jobs = pd.DataFrame(
        {
            "opt_config": [
                "walltime_error",
                "walltime_error",
                "walltime_error",
                "walltime_error",
                "not_yet_submitted",
                "not_yet_submitted",
                "not_yet_submitted",
                "not_yet_submitted",
                "missing_ram_error",
                "missing_ram_error",
                "missing_ram_error",
            ],
            "sp_config": [
                "cancelled",
                "cancelled",
                "cancelled",
                "cancelled",
                "not_yet_submitted",
                "not_yet_submitted",
                "not_yet_submitted",
                "not_yet_submitted",
                "cancelled",
                "cancelled",
                "cancelled",
            ],
        },
        index=[
            "a001_b001",
            "a001_b004_2",
            "a002_b006",
            "a003_b004",
            "a004_b007",
            "a007_b021_2",
            "a007_b022_2",
            "a007_b026",
            "a007_b027",
            "a007_b027_2",
            "a007_b069",
        ],
    )
    expected_df_only_failed_jobs.index.name = "key"
    return expected_df_only_failed_jobs


@pytest.fixture
def expected_df_first_log_jobs(expected_df_only_failed_jobs):
    expected_df_first_log_jobs = expected_df_only_failed_jobs.copy()
    expected_df_first_log_jobs["opt_config"] = [
        "walltime_error",
        "walltime_error",
        "walltime_error",
        "walltime_error",
        "finished",
        "finished",
        "finished",
        "finished",
        "missing_ram_error",
        "missing_ram_error",
        "missing_ram_error",
    ]
    return expected_df_first_log_jobs


@pytest.fixture
def expected_df_second_log_jobs(expected_df_first_log_jobs):
    expected_df_second_log_jobs = expected_df_first_log_jobs.copy()
    expected_df_second_log_jobs["sp_config"] = [
        "cancelled",
        "cancelled",
        "cancelled",
        "cancelled",
        "finished",
        "finished",
        "finished",
        "finished",
        "cancelled",
        "cancelled",
        "cancelled",
    ]
    return expected_df_second_log_jobs
