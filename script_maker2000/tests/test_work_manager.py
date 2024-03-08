import shutil
from pathlib import Path
from script_maker2000.orca import OrcaModule
from script_maker2000.work_manager import WorkManager


def test_workmanager(pre_config_tmp_dir, all_job_ids, monkeypatch):
    def mock_run_job(args, **kw):

        # move output files to output dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        if len(list((orca_test.working_dir / "output").glob("*"))) == 0:
            print("copy data")
            shutil.copytree(
                example_output_files,
                orca_test.working_dir / "output",
                dirs_exist_ok=True,
            )

        return args

    config_path = pre_config_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "sp_config")

    work_manager = WorkManager(orca_test, all_job_ids)
    assert len(work_manager.all_jobs_dict["not_yet_found"]) == 11
    assert len(work_manager.all_jobs_dict["not_yet_prepared"]) == 0

    work_manager.check_input_dir()
    assert len(work_manager.all_jobs_dict["not_yet_found"]) == 0
    assert len(work_manager.all_jobs_dict["not_yet_prepared"]) == 11

    work_manager.prepare_jobs()
    assert len(work_manager.all_jobs_dict["not_yet_prepared"]) == 0
    assert len(work_manager.all_jobs_dict["not_yet_submitted"]) == 11

    orca_input_dirs = list(orca_test.working_dir.glob("input/*"))
    for input_dir in orca_input_dirs:
        assert len(list(input_dir.glob("*.*"))) == 3

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)
    work_manager.submit_jobs()

    assert len(work_manager.all_jobs_dict["not_yet_submitted"]) == 0
    assert len(work_manager.all_jobs_dict["submitted"]) == 11

    work_manager.check_output_dir()
    assert len(work_manager.all_jobs_dict["submitted"]) == 0
    assert len(work_manager.all_jobs_dict["returned_jobs"]) == 11

    work_manager.check_completed_job_status()
    assert len(work_manager.all_jobs_dict["finished"]) == 4
    assert len(work_manager.all_jobs_dict["walltime_error"]) == 4
    assert len(work_manager.all_jobs_dict["missing_ram_error"]) == 3
    assert len(work_manager.all_jobs_dict["unknown_error"]) == 0
    assert len(work_manager.all_jobs_dict["returned_jobs"]) == 0

    assert len(list(work_manager.workModule.working_dir.glob("finished/*"))) == 4
    assert len(list(work_manager.workModule.working_dir.glob("failed/*"))) == 7

    assert len(list(work_manager.input_dir.glob("*"))) == 11
    assert len(list(work_manager.input_dir.glob("*tar*"))) == 11
    assert len(list(work_manager.output_dir.glob("*"))) == 0


def test_workmanager_loop(pre_config_tmp_dir, all_job_ids, monkeypatch):
    def mock_run_job(args, **kw):

        # move output files to output dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        if len(list((orca_test.working_dir / "output").glob("*"))) == 0:
            print("copy data")
            shutil.copytree(
                example_output_files,
                orca_test.working_dir / "output",
                dirs_exist_ok=True,
            )

        return args

    config_path = pre_config_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "sp_config")

    work_manager = WorkManager(orca_test, all_job_ids)
    assert len(work_manager.all_jobs_dict["not_yet_found"]) == 11

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)

    work_manager.loop()
    assert len(work_manager.all_jobs_dict["finished"]) == 4
    assert len(work_manager.all_jobs_dict["walltime_error"]) == 4
    assert len(work_manager.all_jobs_dict["missing_ram_error"]) == 3
    assert len(work_manager.all_jobs_dict["unknown_error"]) == 0
    assert len(work_manager.all_jobs_dict["returned_jobs"]) == 0

    assert len(list(work_manager.workModule.working_dir.glob("finished/*"))) == 4
    assert len(list(work_manager.workModule.working_dir.glob("failed/*"))) == 7

    assert len(list(work_manager.input_dir.glob("*"))) == 11
    assert len(list(work_manager.input_dir.glob("*tar*"))) == 11
    assert len(list(work_manager.output_dir.glob("*"))) == 0
