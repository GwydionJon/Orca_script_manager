from click.testing import CliRunner
import json
import shutil
import pytest
import zipfile
from script_maker2000.cli import config_check, start_config, start_zip, collect_input
from script_maker2000.batch_manager import BatchManager


def test_config_check(clean_tmp_dir, monkeypatch):
    main_config_path = clean_tmp_dir / "example_config.json"
    main_config_path = str(main_config_path)

    runner = CliRunner()
    result = runner.invoke(
        config_check, ["--config", main_config_path], catch_exceptions=False
    )

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

    main_config_path = clean_tmp_dir / "example_config.json"
    main_config_path = str(main_config_path)

    with open(main_config_path, "r") as f:
        config = json.load(f)

    config["main_config"]["wait_for_results_time"] = 0.1

    with open(main_config_path, "w") as f:
        json.dump(config, f)

    original_init = BatchManager.__init__
    BatchManager.__init__ = new_init

    # monkeypatch
    def new_fake_slurm_function(*args, **kwargs):
        raise NotImplementedError("The slurm commands can't be run inside this test")

    monkeypatch.setattr("subprocess.run", new_fake_slurm_function)
    monkeypatch.setattr("shutil.which", lambda x: True)

    runner = CliRunner()
    result = runner.invoke(start_config, ["--config", main_config_path, "--profile"])
    assert "The slurm commands can't be run inside this test" in str(result.exception)
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

    zip_path = prep_path / "input_files.zip"
    extract_path = clean_tmp_dir / "example_prep" / "extracted_test"

    with zipfile.ZipFile(zip_path, "r") as zipf:
        zipf.extractall(path=extract_path)

    expected_files = ["extracted_xyz", "example_config.json", "example_molecules.json"]
    for file in expected_files:
        assert (extract_path / file).exists()
    assert len(list(extract_path.glob("*/*"))) == 11

    result = runner.invoke(
        collect_input, ["--config", "not_a_path", "-o", str(prep_path)]
    )
    assert "No such file or directory" in str(result.exception)
    assert result.exit_code == 1

    new_zip_dir = clean_tmp_dir / "new_tar"
    new_zip_dir.mkdir()
    new_zip_path = new_zip_dir / "new_tar.zip"
    shutil.copy(zip_path, new_zip_path)

    with zipfile.ZipFile(new_zip_path, "r") as zipf:
        zipf.extractall(path=new_zip_dir)

    expected_files = ["extracted_xyz", "example_config.json", "example_molecules.json"]
    for file in expected_files:
        assert (new_zip_dir / file).exists()

    # read new example_molecules file and verify that the new filepath is accurate
    #  and points to the new extracted xyz dir
    with open(new_zip_dir / "example_molecules.json", "r") as f:
        molecules_dict = json.load(f)
    for molecule in molecules_dict.values():
        assert "extracted_xyz" in molecule["path"]


@pytest.mark.skipif(
    shutil.which("sbatch") is not None,
    reason="sbatch not found, this test should only run locally",
)
def test_start_zip_local(clean_tmp_dir, monkeypatch):
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.wait_time = 1
        self.max_loop = 10

    original_init = BatchManager.__init__
    BatchManager.__init__ = new_init

    monkeypatch.setattr("shutil.which", lambda x: True)

    # monkeypatch
    def new_fake_slurm_function(*args, **kwargs):
        raise NotImplementedError("The slurm commands can't be run inside this test")

    monkeypatch.setattr("subprocess.run", new_fake_slurm_function)

    main_config_path = clean_tmp_dir / "example_config.json"
    main_config_path = str(main_config_path)
    prep_path = clean_tmp_dir / "example_prep"
    runner = CliRunner()
    result = runner.invoke(config_check, ["--config", main_config_path])
    assert result.exit_code == 0

    print("test1")
    result = runner.invoke(
        collect_input, ["--config", main_config_path, "-o", str(prep_path)]
    )
    assert result.exit_code == 0

    zip_path = prep_path / "input_files.zip"
    print("test2")
    result = runner.invoke(
        start_zip, ["--zip", zip_path, "-e", str(prep_path)], catch_exceptions=True
    )
    assert "The slurm commands can't be run inside this test" in str(result.exception)
    assert result.exit_code == 1
    BatchManager.__init__ = original_init


@pytest.mark.skipif(
    shutil.which("sbatch") is None,
    reason="sbatch not found, this test should only run on a server",
)
def test_start_zip_remote(clean_tmp_dir, monkeypatch):
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

    zip_path = prep_path / "test.tar.gz"
    result = runner.invoke(start_zip, ["--tar", zip_path, "-e", str(prep_path)])
