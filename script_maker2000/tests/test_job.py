import shutil
import pytest
from script_maker2000.job import Job
import json
import subprocess


@pytest.mark.skipif(shutil.which("squeue") is not None, reason="Slurm available")
def test_job_collect_efficiency_data_local(clean_tmp_dir, monkeypatch):

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
        "key1": 1234,
        "key2": 5678,
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

    assert efficiency_data[1234]["JobID"]
    assert efficiency_data[1234]["JobName"]
    assert efficiency_data[1234]["ExitCode"]
    assert efficiency_data[1234]["NCPUS"]
    assert efficiency_data[1234]["CPUTimeRAW"]
    assert efficiency_data[1234]["ElapsedRaw"]
    assert efficiency_data[1234]["TimelimitRaw"]
    assert efficiency_data[1234]["ConsumedEnergyRaw"]
    assert efficiency_data[1234]["MaxDiskRead"]
    assert efficiency_data[1234]["MaxDiskWrite"]
    assert efficiency_data[1234]["MaxVMSize"]
    assert efficiency_data[1234]["ReqMem"]
    assert efficiency_data[1234]["maxRamUsage"]

    job_export_dict = test_job.export_as_dict()
    assert job_export_dict["efficiency_data"][1234]["MaxVMSize"]

    # test json export
    with open(clean_tmp_dir / "test_job.json", "w") as f:
        json.dump(job_export_dict, f)

    with open(clean_tmp_dir / "test_job.json", "r") as f:
        job_export_dict = json.load(f)

    test_job2 = Job.import_from_dict(job_export_dict, clean_tmp_dir)
    assert test_job2.efficiency_data[1234]["MaxVMSize"]


@pytest.mark.skipif(shutil.which("sbatch") is None, reason="No slurm available.")
def test_job_collection_remote():
    test_job = Job(
        input_id="test_id",
        all_keys=["key1", "key2"],
        working_dir="test_dir",
        charge=0,
        multiplicity=1,
    )
    test_job.slurm_id_per_key = {
        "key1": 12486228,
        "key2": 12486234,
    }

    collection_format_arguments = [
        "jobid",
        "jobname",
        "exitcode",
        "NCPUS",
        "cputimeraw",
        "elapsedraw",
        "timelimitraw",
        "consumedenergyraw",
        "MaxDiskRead",
        "MaxDiskWrite",
        "MaxVMSize",
        "reqmem",
        "MaxRSS",
    ]
    ouput_sacct = subprocess.run(
        [
            shutil.which("sacct"),
            "-j",
            str(12486228),
            "--format",
            ",".join(collection_format_arguments),
            "-p",
        ],
        shell=False,
        check=False,
        capture_output=True,
        text=True,
    )
    print(ouput_sacct.stdout)
    # test_job.collect_efficiency_data()

    # eff_data = test_job.efficiency_data

    # print(eff_data)
    1 / 0
