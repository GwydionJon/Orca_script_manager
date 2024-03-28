import shutil
import pytest
from script_maker2000.job import Job


@pytest.mark.skipif(shutil.which("squeue") is not None, reason="Slurm available")
def test_job_collect_efficiency_data_local(monkeypatch):

    def _mock_subprocess_run(*args, **kwargs):

        class MockCompletedProcess:

            def __init__(
                self,
            ):
                self.returncode = 0
                self.stdout = "JobID|JobName|ExitCode|NCPUS|CPUTimeRAW|ElapsedRaw|TimelimitRaw|ConsumedEnergyRaw|"
                self.stdout += (
                    "MaxDiskRead|MaxDiskWrite|MaxVMSize|ReqMem|MaxRSS|\n1234|"
                )
                self.stdout += "sp_config1_opt_config2__sp_config1___a001_b001|0:0|2|66|33|2|2442||||40M||"
                self.stdout += "\n1234.batch|batch|0:0|2|66|33||2416|160.43M|182.33M|227220K||1656K|"
                self.stdout += "\n1234.extern|extern|0:0|2|66|33||2442|0.00M|0.00M|131840K||720K|\n"

        mock_process = MockCompletedProcess()
        return mock_process

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

    assert test_job.collect_efficiency_data() is None

    monkeypatch.setattr(
        "shutil.which",
        lambda x: True,
    )

    with pytest.raises(TypeError):
        test_job.collect_efficiency_data()

    monkeypatch.setattr("subprocess.run", _mock_subprocess_run)

    test_job.collect_efficiency_data()

    efficiency_data = test_job.efficiency_data

    assert efficiency_data["JobID"]
    assert efficiency_data["JobName"]
    assert efficiency_data["ExitCode"]
    assert efficiency_data["NCPUS"]
    assert efficiency_data["CPUTimeRAW"]
    assert efficiency_data["ElapsedRaw"]
    assert efficiency_data["TimelimitRaw"]
    assert efficiency_data["ConsumedEnergyRaw"]
    assert efficiency_data["MaxDiskRead"]
    assert efficiency_data["MaxDiskWrite"]
    assert efficiency_data["MaxVMSize"]
    assert efficiency_data["ReqMem"]
    assert efficiency_data["maxRamUsage"]

    job_export_dict = test_job.export_as_dict()
    assert job_export_dict["efficiency_data"] == efficiency_data
