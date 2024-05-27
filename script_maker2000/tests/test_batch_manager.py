from pathlib import Path
import shutil
import asyncio
import pytest
import json

from script_maker2000.batch_manager import BatchManager
from script_maker2000.files import read_batch_config_file
from script_maker2000.analysis import extract_infos_from_results


def test_batch_manager(clean_tmp_dir, monkeypatch, fake_slurm_function):

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)

    first_input_dir = batch_manager.working_dir / "working" / "opt_config" / "input"
    assert len(list(first_input_dir.glob("*"))) == 11
    assert len(list(first_input_dir.glob("*/*xyz"))) == 11

    # manually trigger the first worker
    first_worker = list(batch_manager.work_managers.values())[0][0]

    # monkeypatch the job dict into the monkeypatched slurm function
    job_dict = batch_manager.job_dict

    def new_fake_slurm_function(*args, monkey_patch_job_dict=job_dict, **kwargs):
        return fake_slurm_function(
            *args, monkey_patch_job_dict=monkey_patch_job_dict, **kwargs
        )

    monkeypatch.setattr("subprocess.run", new_fake_slurm_function)
    monkeypatch.setattr("shutil.which", lambda x: x)
    monkeypatch.setattr(first_worker, "wait_time", 0.2)
    monkeypatch.setattr(first_worker, "max_loop", 4)
    worker_output = asyncio.run(first_worker.loop())
    assert "All jobs done after " in worker_output

    batch_manager.advance_jobs()
    second_worker = list(batch_manager.work_managers.values())[1][0]
    monkeypatch.setattr(second_worker, "wait_time", 0.2)
    monkeypatch.setattr(second_worker, "max_loop", 5)

    worker_output = asyncio.run(second_worker.loop())
    assert "All jobs done after " in worker_output
    batch_manager.advance_jobs()

    all_results = list(batch_manager.working_dir.glob("finished/raw_results/*"))
    failed = list(batch_manager.working_dir.glob("finished/raw_results/*/failed*"))

    # only the failed jobs should be in the raw results dir
    assert len(all_results) == 11
    assert len(failed) == 7


@pytest.mark.skipif(shutil.which("sbatch") is None, reason="No slurm available.")
def test_batch_loop_no_files(clean_tmp_dir, monkeypatch):

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)

    monkeypatch.setattr(batch_manager, "wait_time", 10)
    monkeypatch.setattr(batch_manager, "max_loop", 10)

    exit_code, task_results = batch_manager.run_batch_processing()
    assert exit_code == 0
    for task_result in task_results:
        assert task_result.done() is True
        assert "done" in task_result.result()


@pytest.mark.skipif(
    shutil.which("sbatch") is not None, reason="Slurm available, use no files test."
)
def test_batch_loop_with_files(clean_tmp_dir, monkeypatch, fake_slurm_function):

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)

    monkeypatch.setattr("shutil.which", lambda x: x)

    monkeypatch.setattr(batch_manager, "wait_time", 0.5)
    monkeypatch.setattr(batch_manager, "max_loop", 12)

    for work_manager_list in batch_manager.work_managers.values():
        for work_manager in work_manager_list:
            monkeypatch.setattr(work_manager, "wait_time", 0.3)
            monkeypatch.setattr(work_manager, "max_loop", 10)

    # monkeypatch the job dict into the monkeypatched slurm function
    job_dict = batch_manager.job_dict

    def new_fake_slurm_function(*args, monkey_patch_job_dict=job_dict, **kwargs):
        return fake_slurm_function(
            *args, monkey_patch_job_dict=monkey_patch_job_dict, **kwargs
        )

    monkeypatch.setattr("subprocess.run", new_fake_slurm_function)

    with pytest.raises(RuntimeError):
        exit_code, task_results = batch_manager.run_batch_processing()
        assert exit_code == 1
        for task_result in task_results:
            assert task_result.done() is True
            assert "All jobs done after" in task_result.result()

    all_results = list(batch_manager.working_dir.glob("finished/raw_results/*"))
    failed = list(batch_manager.working_dir.glob("finished/raw_results/*/failed*"))
    not_failed = list(
        batch_manager.working_dir.glob("finished/raw_results/*/[!failed]*")
    )

    assert len(all_results) == 11
    assert len(failed) == 7
    assert len(not_failed) == 8

    # make sure the global batch config is updated
    config_name = batch_manager.main_config["main_config"]["config_name"]

    batch_config_path = read_batch_config_file("path")

    batch_config = read_batch_config_file("dict")
    working_dir = batch_manager.working_dir

    assert str(working_dir) not in batch_config[config_name]["running"]

    # debug ci
    batch_manager.log.error(batch_config_path)
    batch_manager.log.error(batch_config)
    assert str(working_dir) in batch_config[config_name]["finished"]


def test_parallel_steps(multilayer_tmp_dir, monkeypatch, fake_slurm_function):

    main_config_path = multilayer_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)

    for job in batch_manager.job_dict.values():
        assert len(job.overlapping_jobs) == 1

    if shutil.which("sbatch") is None:
        # test locally
        monkeypatch.setattr("shutil.which", lambda x: x)

        # monkeypatch the job dict into the monkeypatched slurm function
        job_dict = batch_manager.job_dict

        def new_fake_slurm_function(*args, monkey_patch_job_dict=job_dict, **kwargs):
            return fake_slurm_function(
                *args, monkey_patch_job_dict=monkey_patch_job_dict, **kwargs
            )

        monkeypatch.setattr("subprocess.run", new_fake_slurm_function)

        monkeypatch.setattr(batch_manager, "wait_time", 0.1)
        monkeypatch.setattr(batch_manager, "max_loop", 10)

        for work_manager_list in batch_manager.work_managers.values():
            for work_manager in work_manager_list:
                monkeypatch.setattr(work_manager, "wait_time", 0.1)
                monkeypatch.setattr(work_manager, "max_loop", 8)
        with pytest.raises(RuntimeError):
            exit_code, task_results = batch_manager.run_batch_processing()
            assert exit_code == 1
            for task_result in task_results:
                assert task_result.done() is True
                assert "All jobs done after" in task_result.result()
    # if remote
    else:
        monkeypatch.setattr(batch_manager, "wait_time", 10)
        monkeypatch.setattr(batch_manager, "max_loop", -1)

        for work_manager_list in batch_manager.work_managers.values():
            for work_manager in work_manager_list:
                monkeypatch.setattr(work_manager, "wait_time", 10)
                monkeypatch.setattr(work_manager, "max_loop", -1)

        exit_code, task_results = batch_manager.run_batch_processing()
        assert exit_code == 0

        for task_result in task_results:
            assert task_result.done() is True
            assert "All jobs done after" in task_result.result()

    assert len(list(batch_manager.working_dir.glob("finished/raw_results/*"))) == 11

    all_results = list(batch_manager.working_dir.glob("finished/raw_results/*"))
    failed = list(batch_manager.working_dir.glob("finished/raw_results/*/failed/*/*"))
    not_failed = list(
        batch_manager.working_dir.glob("finished/raw_results/*/[!failed]*")
    )

    assert len(all_results) == 11
    assert len(failed) == 14
    assert len(not_failed) == 24

    # assert zip exists
    zip_file = batch_manager.working_dir / "output.zip"
    assert zip_file.exists()

    # check the job_dict

    perform_checks(batch_manager)


def perform_checks(batch_manager):
    with open(batch_manager.working_dir / "job_backup.json", "r") as f:
        job_backup = json.load(f)

    for job in job_backup.values():

        assert len(job["finished_keys"]) <= len(job["all_keys"])

        # get json calc results file
        if job["_current_status"] == "finished":
            job_final_dir = Path(list(job["final_dirs"].values())[0])

            json_file = job_final_dir / f"{job_final_dir.stem}_calc_result.json"
            assert json_file.exists()
            with open(json_file, "r") as f:
                calc_results = json.load(f)

            assert "atomcharges" in calc_results.keys()
            assert calc_results["mult"] == 1

    test_dict, _ = extract_infos_from_results(
        batch_manager.working_dir / "finished/raw_results"
    )

    for key in test_dict.keys():
        assert "dirname" in test_dict[key].keys()
        assert "mult" in test_dict[key].keys()
        assert "charge" in test_dict[key].keys()


def test_continue_run(pre_started_dir, monkeypatch, fake_slurm_function):

    main_config_path = pre_started_dir / "example_config.json"

    batch_manager = BatchManager(main_config_path)
    assert len(list(batch_manager.working_dir.glob("finished/raw_results/*"))) == 0

    if shutil.which("sbatch") is None:
        # test locally
        # monkeypatch the job dict into the monkeypatched slurm function
        job_dict = batch_manager.job_dict

        def new_fake_slurm_function(*args, monkey_patch_job_dict=job_dict, **kwargs):
            return fake_slurm_function(
                *args, monkey_patch_job_dict=monkey_patch_job_dict, **kwargs
            )

        monkeypatch.setattr("subprocess.run", new_fake_slurm_function)
        monkeypatch.setattr("shutil.which", lambda x: x)

        monkeypatch.setattr(batch_manager, "wait_time", 0.14)
        monkeypatch.setattr(batch_manager, "max_loop", 5)

        for work_manager_list in batch_manager.work_managers.values():
            for work_manager in work_manager_list:
                monkeypatch.setattr(work_manager, "wait_time", 0.1)
                monkeypatch.setattr(work_manager, "max_loop", 8)

    else:
        monkeypatch.setattr(batch_manager, "wait_time", 10)
        monkeypatch.setattr(batch_manager, "max_loop", -1)

        for work_manager_list in batch_manager.work_managers.values():
            for work_manager in work_manager_list:
                monkeypatch.setattr(work_manager, "wait_time", 10)
                monkeypatch.setattr(work_manager, "max_loop", -1)

    with pytest.raises(RuntimeError):
        exit_code, task_results = batch_manager.run_batch_processing()
        assert exit_code == 1
        for task_result in task_results:
            assert task_result.done() is True
            assert "All jobs done after" in task_result.result()

    all_results = list(batch_manager.working_dir.glob("finished/raw_results/*"))
    failed = list(batch_manager.working_dir.glob("finished/raw_results/*/failed*"))
    not_failed = list(
        batch_manager.working_dir.glob("finished/raw_results/*/[!failed]*")
    )

    assert len(all_results) == 11
    assert len(failed) == 7
    assert len(not_failed) == 24

    config_name = "continue_run"

    batch_config_path = read_batch_config_file("path")

    batch_config = read_batch_config_file("dict")
    working_dir = batch_manager.working_dir

    assert str(working_dir) not in batch_config[config_name]["running"]

    # debug ci
    batch_manager.log.error(batch_config_path)
    batch_manager.log.error(batch_config)
    assert str(working_dir) in batch_config[config_name]["finished"]
