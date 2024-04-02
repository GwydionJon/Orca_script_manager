from click.testing import CliRunner
import json
import numpy as np
import shutil
import pytest
import tarfile
from script_maker2000.cli import config_check, start_config, start_tar, collect_input
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


@pytest.mark.skipif(
    shutil.which("sbatch") is not None,
    reason="sbatch found, this test should only run on locally",
)
def test_start_config_local(clean_tmp_dir, monkeypatch):

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
    result = runner.invoke(start_config, ["--config", main_config_path])
    assert "FileNotFoundError" in str(result.exception)
    assert result.exit_code == 1
    BatchManager.__init__ = original_init


@pytest.mark.skipif(
    shutil.which("sbatch") is None,
    reason="sbatch not found, this test should only run on a server",
)
def test_start_config_remote(clean_tmp_dir):

    main_config_path = clean_tmp_dir / "example_config.json"
    main_config_path = str(main_config_path)

    with open(main_config_path, "r") as f:
        config = json.load(f)

    config["main_config"]["wait_for_results_time"] = 10

    with open(main_config_path, "w") as f:
        json.dump(config, f)

    runner = CliRunner()
    result = runner.invoke(start_config, ["--config", main_config_path])
    # assert "FileNotFoundError" in str(result.exception)
    assert result.exit_code == 0


def test_collect_files(clean_tmp_dir):

    main_config_path = clean_tmp_dir / "example_config.json"
    main_config_path = str(main_config_path)
    prep_path = clean_tmp_dir / "example_prep"
    runner = CliRunner()
    result = runner.invoke(config_check, ["--config", main_config_path])
    assert result.exit_code == 0

    result = runner.invoke(
        collect_input, ["--config", main_config_path, "-o", str(prep_path)]
    )
    assert result.exit_code == 0
    assert "Tarball created at" in result.output

    tar_path = prep_path / "input_files.tar.gz"
    extract_path = clean_tmp_dir / "example_prep" / "extracted_test"

    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=extract_path, filter="fully_trusted")

    expected_files = ["extracted_xyz", "example_config.json", "example_molecules.csv"]
    for file in expected_files:
        assert (extract_path / file).exists()
    assert len(list(extract_path.glob("*/*"))) == 11

    result = runner.invoke(
        collect_input, ["--config", "not_a_path", "-o", str(prep_path)]
    )
    assert "No such file or directory" in str(result.exception)
    assert result.exit_code == 1

    new_tar_dir = clean_tmp_dir / "new_tar"
    new_tar_dir.mkdir()
    new_tar_path = new_tar_dir / "new_tar.tar.gz"
    shutil.copy(tar_path, new_tar_path)

    with tarfile.open(new_tar_path, "r:gz") as tar:
        tar.extractall(path=new_tar_dir, filter="fully_trusted")

    expected_files = ["extracted_xyz", "example_config.json", "example_molecules.csv"]
    for file in expected_files:
        assert (new_tar_dir / file).exists()


@pytest.mark.skipif(
    shutil.which("sbatch") is not None,
    reason="sbatch not found, this test should only run locally",
)
def test_start_tar_local(clean_tmp_dir, monkeypatch):
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.wait_time = 3
        self.max_loop = 3

    def mock_run_job(args, **kw):
        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    original_init = BatchManager.__init__
    BatchManager.__init__ = new_init

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)

    main_config_path = clean_tmp_dir / "example_config.json"
    main_config_path = str(main_config_path)
    prep_path = clean_tmp_dir / "example_prep"
    runner = CliRunner()
    result = runner.invoke(config_check, ["--config", main_config_path])
    assert result.exit_code == 0

    result = runner.invoke(
        collect_input, ["--config", main_config_path, "-o", str(prep_path)]
    )
    assert result.exit_code == 0

    tar_path = prep_path / "input_files.tar.gz"
    result = runner.invoke(
        start_tar, ["--tar", tar_path, "-e", str(prep_path)], catch_exceptions=True
    )

    assert "FileNotFoundError" in str(result.exception)
    assert result.exit_code == 1
    BatchManager.__init__ = original_init


@pytest.mark.skipif(
    shutil.which("sbatch") is None,
    reason="sbatch not found, this test should only run on a server",
)
def test_start_tar_remote(clean_tmp_dir, monkeypatch):
    main_config_path = clean_tmp_dir / "example_config.json"
    main_config_path = str(main_config_path)
    prep_path = clean_tmp_dir / "example_prep"
    runner = CliRunner()
    result = runner.invoke(config_check, ["--config", main_config_path])
    assert result.exit_code == 0

    result = runner.invoke(
        collect_input,
        ["--config", main_config_path, "-o", str(prep_path)],
        catch_exceptions=True,
    )
    assert result.exit_code == 0
    import traceback

    print(traceback.print_tb(result.exc_info[2]))

    tar_path = prep_path / "test.tar.gz"
    result = runner.invoke(start_tar, ["--tar", tar_path, "-e", str(prep_path)])
