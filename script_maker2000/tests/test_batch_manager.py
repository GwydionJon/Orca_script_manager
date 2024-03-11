from pathlib import Path
import shutil
from script_maker2000.batch_manager import BatchManager
import pandas as pd
import asyncio


def test_batch_manager(clean_tmp_dir, monkeypatch):
    def mock_run_job(args, **kw):

        # move output files to output dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        if len(list((first_worker.output_dir).glob("*"))) == 0:
            print("copy data")
            shutil.copytree(
                example_output_files,
                first_worker.output_dir,
                dirs_exist_ok=True,
            )

        return args

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)
    assert len(batch_manager.all_job_ids) == 11

    # manually trigger the first worker
    first_worker = list(batch_manager.work_managers.values())[0]

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)
    monkeypatch.setattr(first_worker, "wait_time", 0.2)
    monkeypatch.setattr(first_worker, "max_loop", 5)

    worker_output = asyncio.run(first_worker.loop())
    assert worker_output == "All jobs done after 0."

    batch_manager.move_files()
    second_worker = list(batch_manager.work_managers.values())[1]
    monkeypatch.setattr(second_worker, "wait_time", 0.2)
    monkeypatch.setattr(second_worker, "max_loop", 5)

    assert len(list(second_worker.input_dir.glob("*"))) == 4
    worker_output = asyncio.run(second_worker.loop())

    # no handling of failed jobs is done here so the worker will loop until max_loop
    assert worker_output == "Breaking loop after 5."


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

    first_batch_output = batch_manager.start_work_manager_loops()
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

        return args

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)
    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)
    monkeypatch.setattr(batch_manager, "wait_time", 0.3)
    monkeypatch.setattr(batch_manager, "max_loop", 5)

    for work_manager in batch_manager.work_managers.values():
        monkeypatch.setattr(work_manager, "wait_time", 0.1)
        monkeypatch.setattr(work_manager, "max_loop", 2)

    task_results = batch_manager.run_batch_processing()
    for task_result in task_results:
        assert task_result.done() is True
        assert task_result.result() == "Breaking loop after 2."


def test_batch_loop_with_files(clean_tmp_dir, monkeypatch):

    def mock_run_job(args, **kw):

        return args

    main_config_path = clean_tmp_dir / "example_config.json"
    batch_manager = BatchManager(main_config_path)
    print(shutil.which("sbatch"))

    if shutil.which("sbatch") is None:
        # test locally
        monkeypatch.setattr("shutil.which", lambda x: True)
        monkeypatch.setattr("subprocess.run", mock_run_job)

        # copy output files into dir

        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        target_dirs = [
            work_manager.output_dir
            for work_manager in batch_manager.work_managers.values()
        ]

        for target_dir in target_dirs:
            shutil.copytree(
                example_output_files,
                target_dir,
                dirs_exist_ok=True,
            )

        monkeypatch.setattr(batch_manager, "wait_time", 0.3)
        monkeypatch.setattr(batch_manager, "max_loop", 5)

        for work_manager in batch_manager.work_managers.values():
            monkeypatch.setattr(work_manager, "wait_time", 0.3)
            monkeypatch.setattr(work_manager, "max_loop", 2)

    else:
        monkeypatch.setattr(batch_manager, "wait_time", 10)
        monkeypatch.setattr(batch_manager, "max_loop", -1)

        for work_manager in batch_manager.work_managers.values():
            monkeypatch.setattr(work_manager, "wait_time", 10)
            monkeypatch.setattr(work_manager, "max_loop", -1)

    task_results = batch_manager.run_batch_processing()
    for task_result in task_results:
        assert task_result.done() is True
        assert "All jobs done after" in task_result.result()
