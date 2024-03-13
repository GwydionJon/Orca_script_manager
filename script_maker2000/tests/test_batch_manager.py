from pathlib import Path
import shutil
import pandas as pd
import numpy as np
import asyncio
import pytest
from script_maker2000.batch_manager import BatchManager


def test_batch_manager(clean_tmp_dir, monkeypatch):
    def mock_run_job(args, **kw):

        # move output files to output dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        if len(list((first_worker.output_dir).glob("*"))) == 0:
            shutil.copytree(
                example_output_files,
                first_worker.output_dir,
                dirs_exist_ok=True,
            )
            for dir in first_worker.output_dir.glob("*"):
                new_dir = str(dir).replace("START_", "START___")
                new_dir = Path(new_dir)
                new_dir.mkdir()
                for file in dir.glob("*"):
                    new_file = str(file.name).replace("START_", "START___")
                    file.rename(Path(new_dir) / new_file)
                shutil.rmtree(dir)

        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)
    assert len(batch_manager.all_job_ids) == 11

    # manually trigger the first worker
    first_worker = list(batch_manager.work_managers.values())[0]

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)
    monkeypatch.setattr(first_worker, "wait_time", 0.2)
    monkeypatch.setattr(first_worker, "max_loop", 2)

    worker_output = asyncio.run(first_worker.loop())
    assert worker_output == "All jobs done after 0."

    batch_manager.move_files()
    second_worker = list(batch_manager.work_managers.values())[1]
    monkeypatch.setattr(second_worker, "wait_time", 0.2)
    monkeypatch.setattr(second_worker, "max_loop", 2)

    assert len(list(second_worker.input_dir.glob("*"))) == 4
    worker_output = asyncio.run(second_worker.loop())

    # no handling of failed jobs is done here so the worker will loop until max_loop
    assert worker_output == "Breaking loop after 2."


@pytest.mark.skip(reason="Test doesn't work in Github Actions.")
def test_batch_manager_threads(
    clean_tmp_dir,
    monkeypatch,
    expected_df_only_failed_jobs,
    expected_df_first_log_jobs,
    expected_df_second_log_jobs,
):

    def mock_run_job(args, **kw):
        # move output files to output dir
        target_dir = batch_manager.working_dir / "opt_config" / "output"
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"

        if len(list((target_dir).glob("*"))) == 0:
            shutil.copytree(
                example_output_files,
                target_dir,
                dirs_exist_ok=True,
            )
        else:
            target_dir = batch_manager.working_dir / "sp_config" / "output"
            if len(list((target_dir).glob("*"))) == 0:

                shutil.copytree(
                    example_output_files,
                    target_dir,
                    dirs_exist_ok=True,
                )

        return args

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)
    assert len(batch_manager.all_job_ids) == 11

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)

    for work_manager in batch_manager.work_managers.values():
        monkeypatch.setattr(work_manager, "wait_time", 0.2)
        monkeypatch.setattr(work_manager, "max_loop", 2)

    first_batch_output = asyncio.run(batch_manager.start_work_manager_loops())
    assert sorted(list(first_batch_output)) == sorted(
        ["All jobs done after 0.", "Breaking loop after 2."]
    )

    batch_manager.move_files()
    batch_manager.manage_failed_jobs()

    df_only_failed_jobs = pd.read_csv(batch_manager.new_csv_file, index_col=0)
    pd.testing.assert_frame_equal(
        df_only_failed_jobs[["opt_config", "sp_config"]],
        expected_df_only_failed_jobs[["opt_config", "sp_config"]],
    )

    batch_manager.manage_job_logging()
    df_first_log_jobs = pd.read_csv(batch_manager.new_csv_file, index_col=0)
    pd.testing.assert_frame_equal(
        df_first_log_jobs[["opt_config", "sp_config"]],
        expected_df_first_log_jobs[["opt_config", "sp_config"]],
    )

    second_batch_output = batch_manager.start_work_manager_loops()

    assert sorted(list(second_batch_output)) == sorted(
        ["All jobs done after 0.", "All jobs done after 0."]
    )

    batch_manager.move_files()
    assert len(list(batch_manager.working_dir.glob("finished/raw_results/*"))) == 4

    batch_manager.manage_job_logging()
    df_second_log_jobs = pd.read_csv(batch_manager.new_csv_file, index_col=0)
    pd.testing.assert_frame_equal(
        df_second_log_jobs[["opt_config", "sp_config"]],
        expected_df_second_log_jobs[["opt_config", "sp_config"]],
    )


def test_batch_loop_no_files(clean_tmp_dir, monkeypatch):

    def mock_run_job(args, **kw):
        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)

    if shutil.which("sbatch") is None:

        monkeypatch.setattr("shutil.which", lambda x: True)
        monkeypatch.setattr("subprocess.run", mock_run_job)

        monkeypatch.setattr(batch_manager, "wait_time", 0.3)
        monkeypatch.setattr(batch_manager, "max_loop", 5)

        for work_manager in batch_manager.work_managers.values():
            monkeypatch.setattr(work_manager, "wait_time", 0.1)
            monkeypatch.setattr(work_manager, "max_loop", 2)

    else:
        monkeypatch.setattr(batch_manager, "wait_time", 10)
        monkeypatch.setattr(batch_manager, "max_loop", 10)

        for work_manager in batch_manager.work_managers.values():
            monkeypatch.setattr(work_manager, "wait_time", 10)
            monkeypatch.setattr(work_manager, "max_loop", 10)

    task_results = batch_manager.run_batch_processing()
    for task_result in task_results:
        assert task_result.done() is True
        assert task_result.result() == "Breaking loop after 2."


def test_batch_loop_with_files(clean_tmp_dir, monkeypatch):

    def mock_run_job(args, **kw):
        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)

    if shutil.which("sbatch") is None:
        # test locally
        monkeypatch.setattr("shutil.which", lambda x: True)
        monkeypatch.setattr("subprocess.run", mock_run_job)

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
                replacement = "START___"
            elif "sp_config" in str(out_dir):
                replacement = "START__OPT_CONFIG___"
            for dir in out_dir.glob("*"):
                new_dir = str(dir).replace("START_", replacement)
                new_dir = Path(new_dir)
                new_dir.mkdir()
                for file in dir.glob("*"):

                    new_file = str(file.name).replace("START_", replacement)
                    if "slurm" in new_file:
                        new_file = "slurm_output.out"

                    file.rename(Path(new_dir) / new_file)
                shutil.rmtree(dir)

        import time

        time.sleep(1)

        monkeypatch.setattr(batch_manager, "wait_time", 0.3)
        monkeypatch.setattr(batch_manager, "max_loop", 5)

        for work_manager_list in batch_manager.work_managers.values():
            for work_manager in work_manager_list:
                monkeypatch.setattr(work_manager, "wait_time", 0.3)
                monkeypatch.setattr(work_manager, "max_loop", 2)

    else:
        monkeypatch.setattr(batch_manager, "wait_time", 10)
        monkeypatch.setattr(batch_manager, "max_loop", -1)

        for work_manager_list in batch_manager.work_managers.values():
            for work_manager in work_manager_list:
                monkeypatch.setattr(work_manager, "wait_time", 10)
                monkeypatch.setattr(work_manager, "max_loop", -1)

    task_results = batch_manager.run_batch_processing()
    for task_result in task_results:
        assert task_result.done() is True
        assert "All jobs done after" in task_result.result()

    assert len(list(batch_manager.working_dir.glob("finished/raw_results/*"))) == 4


def test_parallel_steps(multilayer_tmp_dir, monkeypatch):

    def mock_run_job(args, **kw):
        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    main_config_path = multilayer_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)

    if shutil.which("sbatch") is None:
        # test locally
        monkeypatch.setattr("shutil.which", lambda x: True)
        monkeypatch.setattr("subprocess.run", mock_run_job)

        # copy output files into dir

        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"

        # move files for opt_config 1 + 2
        working_dir = batch_manager.working_dir
        target_dirs = [
            working_dir / "opt_config1" / "output",
            working_dir / "opt_config2" / "output",
        ]

        for target_dir in target_dirs:
            shutil.copytree(
                example_output_files,
                target_dir,
                dirs_exist_ok=True,
            )
        for out_dir in target_dirs:
            replacement = "START___"
            for dir in out_dir.glob("*"):
                new_dir = str(dir).replace("START_", replacement)
                new_dir = Path(new_dir)
                new_dir.mkdir()
                for file in dir.glob("*"):

                    new_file = str(file.name).replace("START_", replacement)
                    if "slurm" in new_file:
                        new_file = "slurm_output.out"

                    file.rename(Path(new_dir) / new_file)
                shutil.rmtree(dir)

        # move files for sp_config 1 + 2

        succesful_output_ids = ["a004_b007", "a007_b021_2", "a007_b022_2", "a007_b026"]
        succesful_output_dirs = []
        for id in succesful_output_ids:
            output_file = list(example_output_files.glob(f"*{id}*"))[0]
            succesful_output_dirs.append(output_file)

        # copy and rename these files to the target dirs
        target_dirs = [
            working_dir / "sp_config1" / "output",
            working_dir / "sp_config2" / "output",
        ]

        for i in range(2):
            for target_dir in target_dirs:
                print(target_dir)
                for output_dir in succesful_output_dirs:
                    print(output_dir)

                    new_file_path = shutil.copytree(
                        output_dir, target_dir / output_dir.name, dirs_exist_ok=True
                    )

                    new_file_name = target_dir / str(output_dir.name).replace(
                        "START_", f"START__OPT_CONFIG{i+1}___"
                    )
                    new_file_path.rename(new_file_name)

        monkeypatch.setattr(batch_manager, "wait_time", 0.3)
        monkeypatch.setattr(batch_manager, "max_loop", 5)

        for work_manager_list in batch_manager.work_managers.values():
            for work_manager in work_manager_list:
                monkeypatch.setattr(work_manager, "wait_time", 0.3)
                monkeypatch.setattr(work_manager, "max_loop", 2)

    else:
        monkeypatch.setattr(batch_manager, "wait_time", 10)
        monkeypatch.setattr(batch_manager, "max_loop", -1)

        for work_manager_list in batch_manager.work_managers.values():
            for work_manager in work_manager_list:
                monkeypatch.setattr(work_manager, "wait_time", 10)
                monkeypatch.setattr(work_manager, "max_loop", -1)

    task_results = batch_manager.run_batch_processing()
    for task_result in task_results:
        assert task_result.done() is True
        assert "All jobs done after" in task_result.result()

    assert len(list(batch_manager.working_dir.glob("finished/raw_results/*"))) == 8
    assert (
        len(list(batch_manager.working_dir.glob("finished/raw_results/*sp_config1*")))
        == 4
    )
    assert (
        len(list(batch_manager.working_dir.glob("finished/raw_results/*sp_config2*")))
        == 4
    )
    assert len(list(batch_manager.working_dir.glob("finished/raw_results/*opt*"))) == 8
