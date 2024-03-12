import shutil
import subprocess
import pytest
import time
from pathlib import Path
from script_maker2000.orca import OrcaModule


def test_OrcaModule(pre_config_tmp_dir):
    config_path = pre_config_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "sp_config")
    xyz_list = list((orca_test.working_dir / "input").glob("*.xyz"))
    orca_test.prepare_jobs(xyz_list)

    assert len(
        (list(pre_config_tmp_dir.glob("example_xyz_output/sp_config/input/*/*.inp")))
    ) == len(
        list(pre_config_tmp_dir.glob("example_xyz_output/start_input_files/*.xyz"))
    )

    assert len(
        (list(pre_config_tmp_dir.glob("example_xyz_output/sp_config/input/*/*.sbatch")))
    ) == len(
        list(pre_config_tmp_dir.glob("example_xyz_output/start_input_files/*.xyz"))
    )
    # run orca test only when available.
    if shutil.which("orca"):

        # toggle to skip these tests
        skip = True
        if skip is False:

            for input_file in pre_config_tmp_dir.glob(
                "example_xyz_output/sp_config/input/*/*.inp"
            ):

                subprocess.run([shutil.which("orca"), input_file])


def test_orca_submission(pre_config_tmp_dir, monkeypatch):

    def mock_run_job(args, shell, **kw):
        return args

    config_path = pre_config_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "sp_config")
    xyz_list = list((orca_test.working_dir / "input").glob("*.xyz"))
    orca_test.prepare_jobs(xyz_list)

    input_dirs = list(orca_test.working_dir.glob("input/*"))
    print([input_dir.name for input_dir in input_dirs])
    for input_dir in input_dirs:

        if shutil.which("sbatch"):
            process = orca_test.run_job(input_dir)
            time.sleep(0.3)
            assert process.returncode == 0

        else:
            with pytest.raises(ValueError):
                orca_test.run_job(input_dir)

    # test with monkeypatch

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)

    for input_dir in input_dirs:
        process = orca_test.run_job(input_dir)
        sbatch_file = list(input_dir.glob("*.sbatch"))[0]
        assert Path(process[1]) == Path(sbatch_file)
        time.sleep(0.3)
