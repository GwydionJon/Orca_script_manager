import shutil
import subprocess
import pytest
from script_maker2000.orca import OrcaModule


def test_OrcaModule(clean_tmp_dir):
    print(clean_tmp_dir)
    config_path = clean_tmp_dir / "example_config.json"

    # copy input files to module working space
    shutil.copytree(
        clean_tmp_dir / "example_xyz",
        clean_tmp_dir / "example_xyz_output" / "sp_config" / "input",
        dirs_exist_ok=True,
    )

    OrcaModule(config_path, "sp_config")

    assert len(
        (list(clean_tmp_dir.glob("example_xyz_output/sp_config/input/*.inp")))
    ) == len(list(clean_tmp_dir.glob("*/*.xyz")))

    # run orca test only when available.
    if shutil.which("orca"):

        # toggle to skip these tests
        skip = True
        for input in clean_tmp_dir.glob("example_xyz_output/sp_config/input/*.inp"):

            if skip is False:
                process = subprocess.run([shutil.which("orca"), input])

                assert process.returncode == 0
            else:

                pass


def test_orca_submission(clean_tmp_dir):
    config_path = clean_tmp_dir / "example_config.json"

    # copy input files to module working space
    shutil.copytree(
        clean_tmp_dir / "example_xyz",
        clean_tmp_dir / "example_xyz_output" / "sp_config" / "input",
        dirs_exist_ok=True,
    )

    orca_test = OrcaModule(config_path, "sp_config")
    for key in orca_test.slurm_path_dict:

        if shutil.which("sbatch"):
            orca_test.run_job(key)
        else:
            with pytest.raises(FileNotFoundError):
                orca_test.run_job(key)
