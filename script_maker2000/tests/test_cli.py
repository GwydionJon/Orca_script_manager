from click.testing import CliRunner
import json
import numpy as np
from script_maker2000.cli import config_check, start
from script_maker2000.batch_manager import BatchManager


def test_config_check(clean_tmp_dir, monkeypatch):
    main_config_path = clean_tmp_dir / "example_config.json"
    main_config_path = str(main_config_path)

    runner = CliRunner()
    result = runner.invoke(config_check, ["--config", main_config_path])
    assert result.exit_code == 0

    # create a bad config file by removing some keys

    faulty_config_path = clean_tmp_dir / "faulty_config.json"
    with open(main_config_path, "r") as f:
        config = json.load(f)
    del config["main_config"]

    with open(faulty_config_path, "w") as f:
        json.dump(config, f)

    result = runner.invoke(config_check, ["--config", faulty_config_path])
    assert result.exit_code == 1
    assert "main_config" in str(result.exception)

    with open(main_config_path, "r") as f:
        config = json.load(f)

    del config["main_config"]["input_file_path"]

    with open(faulty_config_path, "w") as f:
        json.dump(config, f)

    result = runner.invoke(config_check, ["--config", faulty_config_path])
    assert result.exit_code == 1
    assert "input_file_path" in str(result.exception)

    with open(main_config_path, "r") as f:
        config = json.load(f)

    config["main_config"]["input_file_path"] = "not_a_path"

    with open(faulty_config_path, "w") as f:
        json.dump(config, f)

    result = runner.invoke(config_check, ["--config", faulty_config_path])
    assert result.exit_code == 1
    assert "Can't find input files under" in str(result.exception)

    result = runner.invoke(config_check, ["--config", "not_a_path"])

    assert "No such file or directory" in str(result.exception)


def test_start(clean_tmp_dir, monkeypatch):

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.max_loop = 3

    def mock_run_job(args, **kw):
        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    main_config_path = clean_tmp_dir / "example_config.json"
    main_config_path = str(main_config_path)

    with open(main_config_path, "r") as f:
        config = json.load(f)

    config["main_config"]["wait_for_results_time"] = 0.1

    with open(main_config_path, "w") as f:
        json.dump(config, f)

    original_init = BatchManager.__init__
    BatchManager.__init__ = new_init

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)

    runner = CliRunner()
    result = runner.invoke(start, ["--config", main_config_path])
    assert "FileNotFoundError" in str(result.exception)
    assert result.exit_code == 1
    BatchManager.__init__ = original_init
