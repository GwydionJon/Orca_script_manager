import shutil
import subprocess
import pytest
import time

from script_maker2000.orca import OrcaModule


def test_OrcaModule(clean_tmp_dir):
    config_path = clean_tmp_dir / "example_config.json"

    OrcaModule(config_path, "sp_config")

    assert len(
        (list(clean_tmp_dir.glob("example_xyz_output/sp_config/input/*.inp")))
    ) == len(list(clean_tmp_dir.glob("*/*.xyz")))

    assert len(
        (list(clean_tmp_dir.glob("example_xyz_output/sp_config/input/*.sbatch")))
    ) == len(list(clean_tmp_dir.glob("*/*.xyz")))
    # run orca test only when available.
    if shutil.which("orca"):

        # toggle to skip these tests
        skip = True
        for input in clean_tmp_dir.glob("example_xyz_output/sp_config/input/*.inp"):

            if skip is False:
                subprocess.run([shutil.which("orca"), input])

            else:

                pass


def test_orca_submission(clean_tmp_dir):
    config_path = clean_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "sp_config")
    for key in orca_test.slurm_path_dict:

        if shutil.which("sbatch"):
            process = orca_test.run_job(key)
            time.sleep(0.3)
            assert process.returncode == 0

        else:
            with pytest.raises(FileNotFoundError):
                orca_test.run_job(key)
