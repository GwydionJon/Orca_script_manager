from script_maker2000.orca import OrcaModule
from script_maker2000.work_manager import WorkManager
import asyncio


def test_workmanager(clean_tmp_dir, job_dict, monkeypatch, fake_slurm_function):

    config_path = clean_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "sp_config")
    work_manager = WorkManager(orca_test, job_dict)
    # no files present for sp_config yet
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["not_found"]) == 11

    orca_test = OrcaModule(config_path, "opt_config")
    work_manager = WorkManager(orca_test, job_dict)

    # monkeypatch the job dict into the monkeypatched slurm function
    job_dict = work_manager.job_dict

    def new_fake_slurm_function(*args, monkey_patch_job_dict=job_dict, **kwargs):
        return fake_slurm_function(
            *args, monkey_patch_job_dict=monkey_patch_job_dict, **kwargs
        )

    monkeypatch.setattr("subprocess.run", new_fake_slurm_function)
    monkeypatch.setattr("shutil.which", lambda x: x)

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
    assert len(current_job_dict["returned"]) == 11

    # check on returned jobs
    # manage finished jobs
    fresh_finished, walltime_error_jobs = work_manager.manage_returned_jobs(
        current_job_dict["returned"]
    )

    work_manager.manage_finished_jobs(fresh_finished)

    restarted_jobs, non_resetted_jobs = work_manager.restart_walltime_error_jobs(
        walltime_error_jobs
    )

    assert len(restarted_jobs) == 4
    assert len(non_resetted_jobs) == 0
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["found"]) == 4

    # resubmit the failed jobs
    current_job_dict["not_started"].extend(
        work_manager.prepare_jobs(current_job_dict["found"])
    )
    assert len(current_job_dict["not_started"]) == 4
    current_job_dict["submitted"].extend(
        work_manager.submit_jobs(current_job_dict["not_started"])
    )

    assert len(current_job_dict["submitted"]) == 4

    current_job_dict["returned"].extend(
        work_manager.check_submitted_jobs(current_job_dict["submitted"])
    )
    fresh_finished, walltime_error_jobs = work_manager.manage_returned_jobs(
        current_job_dict["returned"]
    )

    work_manager.manage_finished_jobs(fresh_finished)

    assert len(walltime_error_jobs) == 4

    restarted_jobs, non_resetted_jobs = work_manager.restart_walltime_error_jobs(
        walltime_error_jobs
    )
    assert len(restarted_jobs) == 0
    assert len(non_resetted_jobs) == 4

    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["found"]) == 0

    current_job_dict = work_manager.check_job_status()

    assert len(current_job_dict["finished"]) == 4
    assert len(current_job_dict["failed"]) == 7
    assert len(current_job_dict["not_found"]) == 0
    assert len(current_job_dict["submitted"]) == 0
    assert len(current_job_dict["not_started"]) == 0
    assert len(current_job_dict["returned"]) == 0


def test_submit_file_limit(clean_tmp_dir, job_dict, monkeypatch, fake_slurm_function):

    def new_fake_slurm_function(*args, monkey_patch_job_dict=job_dict, **kwargs):
        return fake_slurm_function(
            *args, monkey_patch_job_dict=monkey_patch_job_dict, **kwargs
        )

    monkeypatch.setattr("subprocess.run", new_fake_slurm_function)
    monkeypatch.setattr("shutil.which", lambda x: x)

    config_path = clean_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "opt_config")
    work_manager = WorkManager(orca_test, job_dict)
    # no files present for sp_config yet
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["found"]) == 11

    # prepare jobs
    current_job_dict["not_started"].extend(
        work_manager.prepare_jobs(current_job_dict["found"])
    )

    # change the max number of jobs to submit
    work_manager.main_config["main_config"]["max_n_jobs"] = 5
    current_job_dict["submitted"].extend(
        work_manager.submit_jobs(current_job_dict["not_started"])
    )
    assert len(current_job_dict["submitted"]) == 5

    current_job_dict["returned"].extend(
        work_manager.check_submitted_jobs(current_job_dict["submitted"])
    )
    returned_jobs, walltime_error_jobs = work_manager.manage_returned_jobs(
        current_job_dict["returned"]
    )

    for job in returned_jobs:
        if job.current_status == "finished":
            job.advance_to_next_key()

    work_manager.main_config["main_config"]["max_n_jobs"] = 2
    current_job_dict = work_manager.check_job_status()

    new_submissions = work_manager.submit_jobs(current_job_dict["not_started"])
    assert len(new_submissions) == 2

    # now see if second work manager runs into the same limitation
    orca_test = OrcaModule(config_path, "sp_config")
    work_manager2 = WorkManager(orca_test, job_dict)

    work_manager2.main_config["main_config"]["max_n_jobs"] = 2
    current_job_dict2 = work_manager2.check_job_status()
    current_job_dict2["not_started"].extend(
        work_manager.prepare_jobs(current_job_dict2["found"])
    )
    current_job_dict2["submitted"].extend(
        work_manager.submit_jobs(current_job_dict2["not_started"])
    )
    assert len(current_job_dict2["submitted"]) == 0


def test_submit_file_limit_multi_layer(
    multilayer_tmp_dir, job_dict_multilayer, monkeypatch, fake_slurm_function
):

    def new_fake_slurm_function(
        *args, monkey_patch_job_dict=job_dict_multilayer, **kwargs
    ):
        return fake_slurm_function(
            *args, monkey_patch_job_dict=monkey_patch_job_dict, **kwargs
        )

    monkeypatch.setattr("subprocess.run", new_fake_slurm_function)
    monkeypatch.setattr("shutil.which", lambda x: x)

    config_path = multilayer_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "opt_config1")
    work_manager = WorkManager(orca_test, job_dict_multilayer)
    # no files present for sp_config yet
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["found"]) == 22

    # prepare jobs
    current_job_dict["not_started"].extend(
        work_manager.prepare_jobs(current_job_dict["found"])
    )

    # change the max number of jobs to submit
    work_manager.main_config["main_config"]["max_n_jobs"] = 5
    current_job_dict["submitted"].extend(
        work_manager.submit_jobs(current_job_dict["not_started"])
    )
    assert len(current_job_dict["submitted"]) == 10


def test_workmanager_loop(clean_tmp_dir, job_dict, monkeypatch, fake_slurm_function):

    config_path = clean_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "opt_config")

    work_manager = WorkManager(orca_test, job_dict)

    # monkeypatch the job dict into the monkeypatched slurm function
    job_dict = work_manager.job_dict

    def new_fake_slurm_function(*args, monkey_patch_job_dict=job_dict, **kwargs):
        return fake_slurm_function(
            *args, monkey_patch_job_dict=monkey_patch_job_dict, **kwargs
        )

    monkeypatch.setattr("subprocess.run", new_fake_slurm_function)

    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["found"]) == 11

    monkeypatch.setattr("shutil.which", lambda x: x)
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
