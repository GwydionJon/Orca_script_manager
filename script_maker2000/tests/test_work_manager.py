import shutil
from script_maker2000.orca import OrcaModule
from script_maker2000.work_manager import WorkManager


def test_workmanager(clean_tmp_dir, all_job_ids, monkeypatch):

    def mock_run_job(args, shell, **kw):
        return args

    config_path = clean_tmp_dir / "example_config.json"

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

    if shutil.which("sbatch") is None:
        monkeypatch.setattr("subprocess.run", mock_run_job)
    work_manager.submit_jobs()

    assert len(work_manager.all_jobs_dict["not_yet_submitted"]) == 0
    assert len(work_manager.all_jobs_dict["submitted"]) == 11

    1 / 0
