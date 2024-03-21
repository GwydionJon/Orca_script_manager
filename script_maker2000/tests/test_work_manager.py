import shutil
from pathlib import Path
from script_maker2000.orca import OrcaModule
from script_maker2000.work_manager import WorkManager
import asyncio
import numpy as np


def test_workmanager(clean_tmp_dir, job_dict, monkeypatch):
    def mock_run_job(args, **kw):

        # move output files to output dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        if len(list((orca_test.working_dir / "output").glob("*"))) == 0:
            shutil.copytree(
                example_output_files,
                orca_test.working_dir / "output",
                dirs_exist_ok=True,
            )
            for dir in (orca_test.working_dir / "output").glob("*"):
                new_dir = str(dir).replace("START_", "opt_config___")
                new_dir = Path(new_dir)
                new_dir.mkdir()
                for file in dir.glob("*"):
                    new_file = str(file.name).replace("START_", "opt_config___")
                    file.rename(Path(new_dir) / new_file)
                shutil.rmtree(dir)

        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    config_path = clean_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "sp_config")
    work_manager = WorkManager(orca_test, job_dict)
    # no files present for sp_config yet
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["not_found"]) == 11

    orca_test = OrcaModule(config_path, "opt_config")
    work_manager = WorkManager(orca_test, job_dict)

    # no files present for sp_config yet
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["not_found"]) == 0
    assert len(current_job_dict["found"]) == 11

    # prepare jobs
    current_job_dict["not_started"].extend(
        work_manager.prepare_jobs(current_job_dict["found"])
    )
    assert len(current_job_dict["not_started"]) == 11

    for dir in (orca_test.working_dir / "input").glob("*"):
        assert len(list(dir.glob("*inp"))) == 1
        assert len(list(dir.glob("*xyz"))) == 1
        assert len(list(dir.glob("*sbatch"))) == 1

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)

    current_job_dict["submitted"].extend(
        work_manager.submit_jobs(current_job_dict["not_started"])
    )

    assert len(current_job_dict["submitted"]) == 11
    assert len(list((orca_test.working_dir / "output").glob("*"))) == 11
    for job in current_job_dict["submitted"]:
        assert job.current_status == "submitted"

    # check on submitted jobs
    current_job_dict["returned"].extend(
        work_manager.check_submitted_jobs(current_job_dict["submitted"])
    )
    # haven't refreshed the job status yet
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["returned"]) == 7
    assert len(current_job_dict["failed"]) == 4

    # check on returned jobs
    # manage finished jobs
    work_manager.manage_returned_jobs(current_job_dict["returned"])

    current_job_dict = work_manager.check_job_status()

    assert len(current_job_dict["finished"]) == 4
    assert len(current_job_dict["failed"]) == 7
    assert len(current_job_dict["not_found"]) == 0
    assert len(current_job_dict["submitted"]) == 0
    assert len(current_job_dict["not_started"]) == 0
    assert len(current_job_dict["returned"]) == 0


def test_workmanager_loop(clean_tmp_dir, job_dict, monkeypatch):
    def mock_run_job(args, **kw):

        # move output files to output dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        if len(list((orca_test.working_dir / "output").glob("*"))) == 0:
            shutil.copytree(
                example_output_files,
                orca_test.working_dir / "output",
                dirs_exist_ok=True,
            )
            for dir in (orca_test.working_dir / "output").glob("*"):
                new_dir = str(dir).replace("START_", "opt_config___")
                new_dir = Path(new_dir)
                new_dir.mkdir()
                for file in dir.glob("*"):
                    new_file = str(file.name).replace("START_", "opt_config___")
                    file.rename(Path(new_dir) / new_file)
                shutil.rmtree(dir)

        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    config_path = clean_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "opt_config")

    work_manager = WorkManager(orca_test, job_dict)
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["found"]) == 11

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)
    monkeypatch.setattr(work_manager, "max_loop", 5)
    monkeypatch.setattr(work_manager, "wait_time", 0.3)

    asyncio.run(work_manager.loop())
    # wait for async to finish
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["finished"]) == 4
    assert len(current_job_dict["failed"]) == 7

    assert len(list(work_manager.finished_dir.glob("*"))) == 4
    assert len(list(work_manager.failed_dir.glob("*/*"))) == 7

    assert len(list(work_manager.input_dir.glob("*"))) == 11
    assert len(list(work_manager.input_dir.glob("*"))) == 11
    assert len(list(work_manager.output_dir.glob("*"))) == 11
