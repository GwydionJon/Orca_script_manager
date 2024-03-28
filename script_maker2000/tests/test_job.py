import shutil
import pytest
from script_maker2000.job import Job


@pytest.mark.skipif(shutil.which("squeue") is not None, reason="Slurm available")
def test_job_collect_efficiency_data_local(monkeypatch):

    def _mock_subprocess_run(*args, **kwargs):
        return None

    test_job = Job(
        input_id="test_id",
        all_keys=["key1", "key2"],
        working_dir="test_dir",
        charge=0,
        multiplicity=1,
    )

    test_job.slurm_id_per_key = {
        "key1": "1234",
        "key2": "5678",
    }

    test_job.current_key = "key1"

    with pytest.raises(FileNotFoundError):
        test_job.collect_efficiency_data()

    monkeypatch.setattr(
        "shutil.which",
        lambda x: True,
    )

    with pytest.raises(TypeError):
        test_job.collect_efficiency_data()

    monkeypatch.setattr(
        "subprocess.run",
    )


@pytest.mark.skipif(shutil.which("squeue") is None, reason="Slurm not available")
def test_job_collect_efficiency_data_remote(monkeypatch):

    def _mock_subprocess_run(*args, **kwargs):
        return None

    test_job = Job(
        input_id="test_id",
        all_keys=["key1", "key2"],
        working_dir="test_dir",
        charge=0,
        multiplicity=1,
    )

    test_job.slurm_id_per_key = {
        "key1": "1234",
        "key2": "5678",
    }

    test_job.current_key = "key1"

    with pytest.raises(FileNotFoundError):
        test_job.collect_efficiency_data()

    monkeypatch.setattr(
        "shutil.which",
        lambda x: True,
    )

    with pytest.raises(TypeError):
        test_job.collect_efficiency_data()

    monkeypatch.setattr(
        "subprocess.run",
    )
