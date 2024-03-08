from pathlib import Path
import shutil
from script_maker2000.batch_manager import BatchManager


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

    first_worker.loop()

    batch_manager.move_files()
    second_worker = list(batch_manager.work_managers.values())[1]
    monkeypatch.setattr(second_worker, "wait_time", 0.2)
    monkeypatch.setattr(second_worker, "max_loop", 5)

    assert len(list(second_worker.input_dir.glob("*"))) == 4
    second_worker.loop()


def test_batch_manager_threads(clean_tmp_dir, monkeypatch):

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
    assert first_batch_output == ["All jobs done after 0.", "Breaking loop after 2."]

    batch_manager.move_files()
    batch_manager.manage_failed_jobs()

    second_batch_output = batch_manager.start_work_manager_loops()
    assert second_batch_output == ["All jobs done after 0.", "All jobs done after 0."]

    batch_manager.move_files()

    assert len(list(batch_manager.working_dir.glob("finished/raw_results/*"))) == 4
