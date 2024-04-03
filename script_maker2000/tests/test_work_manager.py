import shutil
from pathlib import Path
from script_maker2000.orca import OrcaModule
from script_maker2000.work_manager import WorkManager
import asyncio
import numpy as np


def test_workmanager(clean_tmp_dir, job_dict, monkeypatch):
    def mock_run_job(args, **kw):

        # move output files to output dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        if len(list((orca_test.working_dir / "output").glob("*"))) == 0:
            shutil.copytree(
                example_output_files,
                orca_test.working_dir / "output",
                dirs_exist_ok=True,
            )
            for dir in (orca_test.working_dir / "output").glob("*"):
                new_dir = str(dir).replace("START_", "opt_config___")
                new_dir = Path(new_dir)
                new_dir.mkdir()
                for file in dir.glob("*"):
                    new_file = str(file.name).replace("START_", "opt_config___")
                    file.rename(Path(new_dir) / new_file)
                shutil.rmtree(dir)

        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    config_path = clean_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "sp_config")
    work_manager = WorkManager(orca_test, job_dict)
    # no files present for sp_config yet
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["not_found"]) == 11

    orca_test = OrcaModule(config_path, "opt_config")
    work_manager = WorkManager(orca_test, job_dict)

    # no files present for sp_config yet
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["not_found"]) == 0
    assert len(current_job_dict["found"]) == 11

    # prepare jobs
    current_job_dict["not_started"].extend(
        work_manager.prepare_jobs(current_job_dict["found"])
    )
    assert len(current_job_dict["not_started"]) == 11

    for dir in (orca_test.working_dir / "input").glob("*"):
        assert len(list(dir.glob("*inp"))) == 1
        assert len(list(dir.glob("*xyz"))) == 1
        assert len(list(dir.glob("*sbatch"))) == 1

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)

    current_job_dict["submitted"].extend(
        work_manager.submit_jobs(current_job_dict["not_started"])
    )

    assert len(current_job_dict["submitted"]) == 11
    assert len(list((orca_test.working_dir / "output").glob("*"))) == 11
    for job in current_job_dict["submitted"]:
        assert job.current_status == "submitted"

    # check on submitted jobs
    current_job_dict["returned"].extend(
        work_manager.check_submitted_jobs(current_job_dict["submitted"])
    )
    # haven't refreshed the job status yet
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["returned"]) == 11

    # check on returned jobs
    # manage finished jobs
    work_manager.manage_returned_jobs(current_job_dict["returned"])

    current_job_dict = work_manager.check_job_status()

    assert len(current_job_dict["finished"]) == 4
    assert len(current_job_dict["failed"]) == 7
    assert len(current_job_dict["not_found"]) == 0
    assert len(current_job_dict["submitted"]) == 0
    assert len(current_job_dict["not_started"]) == 0
    assert len(current_job_dict["returned"]) == 0


def test_workmanager_loop(clean_tmp_dir, job_dict, monkeypatch):
    def mock_run_job(args, **kw):

        # move output files to output dir
        example_output_files = Path(__file__).parent / "test_data" / "example_outputs"
        if len(list((orca_test.working_dir / "output").glob("*"))) == 0:
            shutil.copytree(
                example_output_files,
                orca_test.working_dir / "output",
                dirs_exist_ok=True,
            )
            for dir in (orca_test.working_dir / "output").glob("*"):
                new_dir = str(dir).replace("START_", "opt_config___")
                new_dir = Path(new_dir)
                new_dir.mkdir()
                for file in dir.glob("*"):
                    new_file = str(file.name).replace("START_", "opt_config___")
                    file.rename(Path(new_dir) / new_file)
                shutil.rmtree(dir)

        class TestClass:
            def __init__(self, args, **kw):
                self.args = args
                self.kw = kw
                self.stdout = f"COMPLETED job {np.random.randint(100)}"

        test = TestClass(args, **kw)
        return test

    config_path = clean_tmp_dir / "example_config.json"

    orca_test = OrcaModule(config_path, "opt_config")

    work_manager = WorkManager(orca_test, job_dict)
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["found"]) == 11

    monkeypatch.setattr("shutil.which", lambda x: True)
    monkeypatch.setattr("subprocess.run", mock_run_job)
    monkeypatch.setattr(work_manager, "max_loop", 5)
    monkeypatch.setattr(work_manager, "wait_time", 0.3)

    asyncio.run(work_manager.loop())
    # wait for async to finish
    current_job_dict = work_manager.check_job_status()
    assert len(current_job_dict["finished"]) == 4
    assert len(current_job_dict["failed"]) == 7

    assert len(list(work_manager.finished_dir.glob("*"))) == 4
    assert len(list(work_manager.failed_dir.glob("*/*"))) == 7

    assert len(list(work_manager.input_dir.glob("*"))) == 11
    assert len(list(work_manager.input_dir.glob("*"))) == 11
    assert len(list(work_manager.output_dir.glob("*"))) == 11


# def test_collect_job_data(clean_tmp_dir, monkeypatch):
#     # seff ID:
#     # output_seff = "Job ID: 12441062 "
#     # "Cluster: justus2 "
#     # User/Group: hd_uo452/hd_hd
#     # State: COMPLETED (exit code 0)
#     # Nodes: 1
#     # Cores per node: 12
#     # CPU Utilized: 00:00:28
#     # CPU Efficiency: 6.48% of 00:07:12 core-walltime
#     # Job Wall-clock time: 00:00:36
#     # Memory Utilized: 1.20 MB
#     # Memory Efficiency: 0.50% of 240.00 MB

#     # sacct -j 12441073 --format=jobid,jobname,exitcode,NCPUS,cputimeraw,elapsedraw,
#     # timelimitraw,consumedenergyraw,MaxDiskRead,MaxDiskWrite,MaxVMSize,reqmem,TRESUsageInTot -p
#     ouput_sacct = str(
#         "JobID|JobName|ExitCode|NCPUS|CPUTimeRAW|ElapsedRaw|TimelimitRaw|"
#         + "ConsumedEnergyRaw|MaxDiskRead|MaxDiskWrite|MaxVMSize|ReqMem|TRESUsageInTot|"
#     )
#     ouput_sacct += "12441073|sp_config_opt_config__sp_config___a002_b006|0:0|2|66|33|2|2094||||40M||"
#     ouput_sacct += "12441073.batch|batch|0:0|2|66|33||2067|141.34M|145.87M|227220K|"
#     ouput_sacct+="|cpu=00:00:00,energy=2067,fs/disk=148210812,mem=1965K,pages=0,vmem=227220K|"
#     ouput_sacct += "12441073.extern|extern|0:0|2|66|33||2094|0.00M|0.00M|131828K|"
#     ouput_sacct+="|cpu=00:00:00,energy=2094,fs/disk=2332,mem=516K,pages=0,vmem=131828K|"


# # print(ouput_sacct.split("|"))

# ouput_sacct_split = ouput_sacct.split("|")
# import re

# # split at first digit to seperate header from data
# header = re.split(r"(\d)", ouput_sacct, 1)[0]

# # number of header is number of | -1
# header_names = header.split("|")[:-1]

# print(header_names)
# print("")
# print("")

# data = {}

# for i, header_name in enumerate(header_names):

#     output_split = ouput_sacct_split[i :: len(header_names)][1:]

#     if i == 0:
#         output_split = output_split[:-1]

#     print(i, header_name)
#     print(output_split)
#     print("")
#     if header_name == "JobID":
#         data[header_name] = output_split
#     elif header_name in ["TRESUsageInTot"]:
#         match = [re.search(r"mem=(\d+\w)", column) for column in output_split]
#         match = [m.group(1) if m else None for m in match]
#         data["max_ram_usage"] = match

#     else:
#         data[header_name] = output_split

# print(data)
# for key, value in data.items():
#     print(key, len(value))

# from pint import UnitRegistry

# ureg = UnitRegistry()

# def convert_order_of_magnitude(value):

#     if "K" in value:
#         scaling = 1000
#     elif "M" in value:
#         scaling = 1000000
#     elif "G" in value:
#         scaling = 1000000000
#     elif "T" in value:
#         scaling = 1000000000000
#     elif "P" in value:
#         scaling = 1000000000000000
#     else:
#         scaling = 1

#     return float(value[:-1]) * scaling

# filtered_data = {}

# for key, value in data.items():
#     if key == "JobID":
#         filtered_data[key] = value[0]
#     elif key == "JobName":
#         filtered_data[key] = value[0]
#     elif key == "ExitCode":
#         filtered_data[key] = value[0]
#     elif key == "NCPUS":
#         filtered_data[key] = value[0]
#     elif key == "CPUTimeRAW":
#         filtered_data[key] = value[0] * ureg.second
#     elif key == "ElapsedRaw":
#         filtered_data[key] = value[0] * ureg.second
#     elif key == "TimelimitRaw":
#         filtered_data[key] = value[0] * ureg.minute
#     elif key == "ConsumedEnergyRaw":
#         filtered_data[key] = value[0] * ureg.joule
#     elif key == "MaxDiskRead":
#         filtered_data[key] = convert_order_of_magnitude(value[1]) * ureg.byte
#     elif key == "MaxDiskWrite":
#         filtered_data[key] = convert_order_of_magnitude(value[1]) * ureg.byte
#     elif key == "MaxVMSize":
#         filtered_data[key] = convert_order_of_magnitude(value[1]) * ureg.byte
#     elif key == "ReqMem":
#         filtered_data[key] = convert_order_of_magnitude(value[0]) * ureg.byte
#     elif key == "max_ram_usage":
#         filtered_data[key] = convert_order_of_magnitude(value[1]) * ureg.byte

# print(filtered_data)

# import pandas as pd

# df = pd.DataFrame(data)
# df.replace("", np.nan, inplace=True)
# df.ffill(inplace=True)

# print(df[["JobID", "ReqMem"]])
# print(df.loc[df["JobID"] == "12441073.batch"].to_json(orient="records"))

# df.to_csv("test.csv")
