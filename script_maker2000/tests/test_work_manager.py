from script_maker2000.orca import OrcaModule
from script_maker2000.work_manager import WorkManager


def test_workmanager(clean_tmp_dir, all_job_ids):
    config_path = clean_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "sp_config")

    work_manager = WorkManager(orca_test, all_job_ids)
    assert len(work_manager.all_jobs_dict["not_yet_found"]) == 11
    assert len(work_manager.all_jobs_dict["not_yet_submitted"]) == 0

    work_manager.check_input_dir()
    assert len(work_manager.all_jobs_dict["not_yet_found"]) == 0
    assert len(work_manager.all_jobs_dict["not_yet_submitted"]) == 11

    1 / 0
