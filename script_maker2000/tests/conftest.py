import pytest
from tempfile import mkdtemp
import json
import pathlib
import shutil


@pytest.fixture
def main_dict():
    main_dict = {
        "main_config": {
            "continue_previous_run": False,
            "max_n_jobs": 20,
            "max_ram_per_core": 2500,
            "max_nodes": 50,
            "output_dir": "example_output",
            "max_run_time": "60:00:00",
            "input_file_path": "some_path",
            "input_type": "csv",
            "csv_smiles_column": "smiles",
        },
        "crest_config": {
            "n_tasks": 20,
            "n_cores": 40,
            "ram_per_core": 2000,
            "args": {},
        },
        "opt_config": {
            "method": "Some DFT",
            "basisset": "Some basisset",
            "ram_per_core": 2000,
            "n_cores_per_calculation": 12,
            "n_calculation_at_once": 30,
            "disk_storage": 0,
            "walltime": "40:00:00",
            "args": {},
        },
        "sp_config": {
            "method": "Some better DFT",
            "basisset": "Some better basisset",
            "ram_per_core": 2000,
            "n_cores_per_calculation": 12,
            "n_calculation_at_once": 30,
            "disk_storage": 0,
            "walltime": "40:00:00",
            "args": {},
        },
        "structure_check_config": {"run_checks": True},
        "analysis_config": {"run_benchmark": True},
    }
    return main_dict


@pytest.fixture
def temp_work_dir(main_dict):
    tmp_dir = pathlib.Path(mkdtemp())
    main_dict["main_config"]["output_dir"] = str((tmp_dir / "output"))

    current_path = pathlib.Path(__file__)
    example_mol_csv = (
        current_path / ".." / ".." / "data" / "example_molecules.csv"
    ).resolve()

    example_csv = shutil.copy(example_mol_csv, tmp_dir)
    main_dict["main_config"]["input_file_path"] = str(example_csv)

    with open(tmp_dir / "example_config.json", "w") as json_file:
        json.dump(main_dict, json_file)

    return tmp_dir
