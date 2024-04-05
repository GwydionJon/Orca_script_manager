from pathlib import Path
import shutil
import asyncio
import pytest
import logging
import time
from script_maker2000.batch_manager import BatchManager


def test_batch_manager(clean_tmp_dir, monkeypatch, fake_slurm_function):
    def move_files():

        # move output files to output dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        if len(list((first_worker.output_dir).glob("*"))) == 0:
            shutil.copytree(
                example_output_files,
                first_worker.output_dir,
                dirs_exist_ok=True,
            )
            for dir_ in first_worker.output_dir.glob("*"):
                new_dir = str(dir_).replace("START_", "opt_config___")
                new_dir = Path(new_dir)
                new_dir.mkdir()
                for file in dir_.glob("*"):
                    new_file = str(file.name).replace("START_", "opt_config___")
                    file.rename(Path(new_dir) / new_file)
                shutil.rmtree(dir_)

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)

    first_input_dir = batch_manager.working_dir / "working" / "opt_config" / "input"
    assert len(list(first_input_dir.glob("*"))) == 11
    assert len(list(first_input_dir.glob("*/*xyz"))) == 11

    # manually trigger the first worker
    first_worker = list(batch_manager.work_managers.values())[0][0]

    # monkeypatch the job dict into the monkeypatched slurm function
    job_dict = batch_manager.job_dict

    def new_fake_slurm_function(*args, monkey_patch_test=job_dict, **kwargs):
        move_files()
        return fake_slurm_function(*args, monkey_patch_test=monkey_patch_test, **kwargs)

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

    all_results = list(batch_manager.working_dir.glob("finished/raw_results/*"))
    failed = list(batch_manager.working_dir.glob("finished/raw_results/*/failed*"))

    # only the failed jobs should be in the raw results dir
    assert len(all_results) == 7
    assert len(failed) == 7


@pytest.mark.skipif(shutil.which("sbatch") is None, reason="No slurm available.")
def test_batch_loop_no_files(clean_tmp_dir, monkeypatch):

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)

    monkeypatch.setattr(batch_manager, "wait_time", 10)
    monkeypatch.setattr(batch_manager, "max_loop", 10)

    for work_manager in batch_manager.work_managers.values():
        monkeypatch.setattr(work_manager, "wait_time", 10)
        monkeypatch.setattr(work_manager, "max_loop", 10)

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

    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):  # Just to be sure it is a Logger object
            logger.setLevel(logging.WARNING)

    # test locally
    monkeypatch.setattr("shutil.which", lambda x: x)

    # copy output files into dir

    example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
    target_dirs = []
    for work_manager_list in batch_manager.work_managers.values():
        for work_manager in work_manager_list:
            target_dirs.append(work_manager.output_dir)

    for target_dir in target_dirs:
        shutil.copytree(
            example_output_files,
            target_dir,
            dirs_exist_ok=True,
        )
    # move example output files to output dirs and replace name for new naming scheme
    for out_dir in target_dirs:

        if "opt_config" in str(out_dir):
            replacement = "opt_config___"
        elif "sp_config" in str(out_dir):
            replacement = "opt_config__sp_config___"
        for dir_ in out_dir.glob("*"):
            new_dir = str(dir_).replace("START_", replacement)
            new_dir = Path(new_dir)
            new_dir.mkdir()
            for file in dir_.glob("*"):

                new_file = str(file.name).replace("START_", replacement)
                if "slurm" in new_file:
                    new_file = "slurm_output.out"

                file.rename(Path(new_dir) / new_file)
            shutil.rmtree(dir_)

    time.sleep(1)

    monkeypatch.setattr(batch_manager, "wait_time", 0.5)
    monkeypatch.setattr(batch_manager, "max_loop", 8)

    for work_manager_list in batch_manager.work_managers.values():
        for work_manager in work_manager_list:
            monkeypatch.setattr(work_manager, "wait_time", 0.3)
            monkeypatch.setattr(work_manager, "max_loop", 6)

    # monkeypatch the job dict into the monkeypatched slurm function
    job_dict = batch_manager.job_dict

    def new_fake_slurm_function(*args, monkey_patch_test=job_dict, **kwargs):
        return fake_slurm_function(*args, monkey_patch_test=monkey_patch_test, **kwargs)

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

        def new_fake_slurm_function(*args, monkey_patch_test=job_dict, **kwargs):
            return fake_slurm_function(
                *args, monkey_patch_test=monkey_patch_test, **kwargs
            )

        monkeypatch.setattr("subprocess.run", new_fake_slurm_function)

        # copy output files into dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"

        # move files for opt_config 1 + 2
        working_dir = batch_manager.working_dir
        target_dirs = [
            working_dir / "working" / "opt_config1" / "output",
            working_dir / "working" / "opt_config2" / "output",
        ]

        for target_dir in target_dirs:
            shutil.copytree(
                example_output_files,
                target_dir,
                dirs_exist_ok=True,
            )
        for i, out_dir in enumerate(target_dirs):
            replacement = f"opt_config{i+1}___"
            for dir_ in out_dir.glob("*"):
                new_dir = str(dir_).replace("START_", replacement)
                new_dir = Path(new_dir)
                new_dir.mkdir()
                for file in dir_.glob("*"):

                    new_file = str(file.name).replace("START_", replacement)
                    if "slurm" in new_file:
                        new_file = "slurm_output.out"

                    file.rename(Path(new_dir) / new_file)
                shutil.rmtree(dir_)

        # move files for sp_config 1 + 2

        succesful_output_ids = ["a004_b007", "a007_b021_2", "a007_b022_2", "a007_b026"]
        succesful_output_dirs = []
        for id in succesful_output_ids:
            output_file = list(example_output_files.glob(f"*{id}*"))[0]
            succesful_output_dirs.append(output_file)

        # copy and rename these files to the target dirs
        target_dirs = [
            working_dir / "working" / "sp_config1" / "output",
            working_dir / "working" / "sp_config2" / "output",
        ]

        copy_output(target_dirs, succesful_output_dirs)

        # this will get a bit ugly but i need to
        # overwrite at least one of the slurm output files for the second run
        # with a walltime error

        # copy output file from opt_config1___a001_b001 to opt_config1_sp_config1___a004_b006
        # and overwrite the slurm output file
        src_file = (
            working_dir
            / "working"
            / "opt_config1"
            / "output"
            / "opt_config1___a001_b001"
            / "slurm_output.out"
        )
        target_file = (
            working_dir
            / "working"
            / "sp_config1"
            / "output"
            / "opt_config1__sp_config1___a004_b007"
            / "slurm_output.out"
        )
        shutil.copy(src_file, target_file)

        # copy and then rename the orca output file
        src_file = (
            working_dir
            / "working"
            / "opt_config1"
            / "output"
            / "opt_config1___a001_b001"
            / "opt_config1___a001_b001.out"
        )
        target_file = (
            working_dir
            / "working"
            / "sp_config1"
            / "output"
            / "opt_config1__sp_config1___a004_b007"
            / "opt_config1__sp_config1___a004_b007.out"
        )
        shutil.copy(src_file, target_file)

        monkeypatch.setattr(batch_manager, "wait_time", 0.14)
        monkeypatch.setattr(batch_manager, "max_loop", 8)

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

    # for list_, name in zip(
    #     [all_results, failed, not_failed], ["all", "failed", "not_failed"]
    # ):
    #     print(name)
    #     for value in list_:
    #         if name == "failed":
    #             print(
    #                 value.parent.parent.name,
    #                 value.parent.parent.name,
    #                 value.parent.name,
    #                 value.name,
    #             )
    #         else:
    #             print(value.parent.name, value.name)

    #     print()

    assert len(all_results) == 11
    assert len(failed) == 15
    assert len(not_failed) == 23


def copy_output(target_dirs, succesful_output_dirs):
    for i in range(2):
        for target_dir in target_dirs:
            for output_dir in succesful_output_dirs:
                new_dir_path = shutil.copytree(
                    output_dir, target_dir / output_dir.name, dirs_exist_ok=True
                )
                if "sp_config1" in str(target_dir):
                    j = 1
                else:
                    j = 2

                new_dir_name = target_dir / str(output_dir.name).replace(
                    "START_", f"opt_config{i+1}__sp_config{j}___"
                )
                new_dir_path.rename(new_dir_name)
                for file in new_dir_name.glob("*"):
                    new_file = str(file.name).replace(
                        "START_", f"opt_config{i+1}__sp_config{j}___"
                    )
                    if "slurm" in new_file:
                        new_file = "slurm_output.out"

                    file.rename(new_dir_name / new_file)


def test_continue_run(pre_started_dir, monkeypatch, fake_slurm_function):

    main_config_path = pre_started_dir / "example_config.json"
    with pytest.raises(FileExistsError):
        BatchManager(main_config_path)

    batch_manager = BatchManager(main_config_path, override_continue_job=True)
    assert len(list(batch_manager.working_dir.glob("finished/raw_results/*"))) == 0

    if shutil.which("sbatch") is None:
        # test locally
        # monkeypatch the job dict into the monkeypatched slurm function
        job_dict = batch_manager.job_dict

        def new_fake_slurm_function(*args, monkey_patch_test=job_dict, **kwargs):
            return fake_slurm_function(
                *args, monkey_patch_test=monkey_patch_test, **kwargs
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
