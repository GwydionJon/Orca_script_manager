import logging
import asyncio
from collections import defaultdict
import time
import subprocess
import shutil

import pandas as pd
from io import StringIO
from pint import UnitRegistry

from script_maker2000.job import Job


possible_layer_types = ["orca"]
possible_resource_settings = ["normal", "large", "custom"]


class WorkManager:

    def __init__(self, WorkModule, job_dict: Job) -> None:
        """
        Initializes a WorkManager object.

        This class is used to manage the work of a WorkModule.
        It checks if new files are available and submits them to the server while
        keeping below the maximum number of jobs.
        It also checks if jobs are finished and handles the output files.
        Failed jobs are collected and logged.

        Args:
            WorkModule (type): The WorkModule object associated with this WorkManager.
            job_dict (Job): The dictionary of jobs associated with this WorkManager.
        """

        self.main_config = WorkModule.main_config
        self.workModule = WorkModule
        self.job_dict = job_dict

        self.ureg = UnitRegistry(cache_folder=":auto:")

        self.config_key = self.workModule.config_key
        self.module_config = WorkModule.internal_config
        self.step_id = self.module_config["step_id"]
        self.log = logging.getLogger(self.workModule.config_key)

        self.input_dir = self.workModule.working_dir / "input"
        self.output_dir = self.workModule.working_dir / "output"
        self.finished_dir = self.workModule.working_dir / "finished"
        self.failed_dir = self.workModule.working_dir / "failed"

        self.is_finished = False

        # This way the wait time can be adjusted with monkeypatch for faster testing
        self.wait_time = self.main_config["main_config"]["wait_for_results_time"]
        self.max_loop = -1  # -1 means infinite loop until all jobs are done
        # Change max loop with monkeypatch for testing

    # check input dir
    # check output dir
    # submit jobs
    # catch submit errors
    # check job status
    # manage failed jobs
    # manage finished jobs
    # loop
    # check if all jobs are done

    def check_job_status(self, ignore_overlapping_jobs=True):
        """Go over all jobs and check their status for this work manager."""

        current_job_dict = defaultdict(list)
        current_key = self.config_key
        for job_id, job in self.job_dict.items():
            status_result = job.check_status_for_key(
                current_key, ignore_overlapping_jobs=ignore_overlapping_jobs
            )
            if status_result == "not_assigned":
                # this job is not assigned to this work manager
                # and will be skipped
                continue

            current_job_dict[status_result].append(job)
            # possible status results:
            # not_assigned, not_started, found, submitted, finished, failed

        return current_job_dict

    def prepare_jobs(self, found_jobs):

        input_dirs = []
        charge_list = []
        multiplicity_list = []
        for job in found_jobs:

            input_dirs.append(job.current_dirs["input"])

            charge_list.append(job.charge)
            multiplicity_list.append(job.multiplicity)

        input_dir_dict = self.workModule.prepare_jobs(
            input_dirs, charge_list=charge_list, multiplicity_list=multiplicity_list
        )

        self.log.info(f"Prepared {len(input_dir_dict)} new jobs.")

        for job in found_jobs:
            job.current_status = "not_started"

        return found_jobs

    def submit_jobs(self, not_started_jobs):
        """
        Submits a list of jobs for execution.

        Args:
            not_started_jobs (list): A list of Job objects that have not been started yet.

        Returns:
            list: A list of Job objects that have been submitted for execution.
        """
        # check if the total number of submitted jobs is below the maximum
        total_running_jobs = 0
        max_jobs = self.main_config["main_config"]["max_n_jobs"]
        for job in self.job_dict.values():
            if job.current_status == "submitted":
                total_running_jobs += 1

        started_jobs = []
        overlapping_jobs = []
        for job in not_started_jobs:
            if job.current_status == "not_started":
                if total_running_jobs >= max_jobs:
                    continue

                process = self.workModule.run_job(job)
                job_id = int(process.stdout.split("job ")[1])
                job.slurm_id_per_key[self.config_key] = job_id
                job.current_status = "submitted"
                total_running_jobs += 1
                started_jobs.append(job)
                time.sleep(0.2)
            elif job.current_status == "submitted_overlapping_job":
                overlapping_jobs.append(job)

        self.log.info(
            "Only %d (+%d overlapping jobs) out of %d jobs were submitted due to max job limit of %d."
            % (
                len(started_jobs),
                len(overlapping_jobs),
                len(not_started_jobs),
                max_jobs,
            )
        )

        self.log.info(
            "Submitted %d new jobs with %d overlapping jobs."
            % (len(started_jobs), len(overlapping_jobs))
        )

        if len(started_jobs) != len(not_started_jobs):
            self.log.info(
                f"Only {len(started_jobs)} (+{len(overlapping_jobs)} overlapping jobs) out of {len(not_started_jobs)} "
                + f"jobs were submitted due to max job limit of {max_jobs}."
            )

        total_started_jobs = started_jobs + overlapping_jobs
        return total_started_jobs

    def _get_slurm_sacct_output(self, slurm_ids, sacct_format_keys):

        slurm_ids = ",".join([str(slurm_id) for slurm_id in slurm_ids])
        collection_format_arguments = ",".join(sacct_format_keys)

        ouput_sacct = subprocess.run(
            [
                shutil.which("sacct"),
                "-j",
                slurm_ids,
                "--format",
                collection_format_arguments,
                "-p",
            ],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
        )

        data_io = StringIO(ouput_sacct.stdout.strip())
        df = pd.read_csv(data_io, sep="|", index_col=False)

        return df

    def check_submitted_jobs(self, submitted_jobs):
        """
        Find new jobs in the output directory and check if they have returned.

        Args:
            submitted_jobs (list): A list of submitted jobs.

        Returns:
            list: A list of finished jobs.

        """
        job_slurm_ids = {
            job.slurm_id_per_key[self.config_key]: job for job in submitted_jobs
        }

        # select which columns to collect
        sacct_format_keys = ["JobID", "JobName", "State"]
        finished_jobs = []

        if not job_slurm_ids:
            return finished_jobs

        slurm_df = self._get_slurm_sacct_output(job_slurm_ids.keys(), sacct_format_keys)
        self.log.debug(slurm_df)

        # remove lines with batch and extern
        slurm_df = slurm_df[~slurm_df["JobName"].str.contains("batch|extern")]
        for slurm_id, job in job_slurm_ids.items():
            slurm_job = slurm_df[slurm_df["JobID"].astype(int) == int(slurm_id)]
            if slurm_job.empty:
                continue

            slurm_job = slurm_job.iloc[0]
            slurm_state = slurm_job["State"]

            if slurm_state in ["COMPLETED", "TIMEOUT", "FAILED", "CANCELLED"]:
                job.current_status = "returned"
                finished_jobs.append(job)

        self.log.info(
            "Collected %d returned jobs from %d submitted jobs.",
            len(finished_jobs),
            len(submitted_jobs),
        )

        return finished_jobs

    def manage_returned_jobs(self, returned_jobs):
        """
        Manages the returned jobs by checking their status and performing necessary actions.

        Args:
            returned_jobs (list): A list of Job objects representing the returned jobs.

        Returns:
            tuple: A tuple containing two lists:
                - The first list contains the remaining returned jobs after processing.
                - The second list contains the jobs that encountered walltime errors and need to be restarted.
        """
        # get job status from work module
        return_status_dict = defaultdict(lambda: 0)
        overlapping_jobs_info = []
        non_existing_output = []
        reset_jobs = []

        for job in returned_jobs:
            # first check if the job was successful and
            # if the job was already performed by an overlapping job
            if job.check_status_for_key(self.config_key) != "returned":
                overlapping_jobs_info.append(
                    f"Job {job.unique_job_id} was already handled due to overlapping jobs."
                )
                continue

            if not job.current_dirs["output"].exists():
                non_existing_output.append(job)
                self.log.warning(
                    "Job %s has no output dir under %s.",
                    job.unique_job_id,
                    job.current_dirs["output"],
                )
                continue

            work_module_status = self.workModule.check_job_status(job)

            # check if status is walltime error, if skip the return manager

            job_reset = job.manage_return(work_module_status)

            if job_reset:
                reset_jobs.append(job)
                return_status_dict["reset"] += 1
                continue

            return_status_dict[work_module_status] += 1

        # remove empty jobs
        for job in non_existing_output:
            returned_jobs.remove(job)

        # remove walltime error jobs that will be restarted
        for job in reset_jobs:
            returned_jobs.remove(job)

        self.log.info(
            "Skipped %d overlapping jobs as they are already done.",
            len(overlapping_jobs_info),
        )

        if non_existing_output:
            error_message = (
                "Caught %d non existing output dirs after slurm was finished."
            )
            self.log.warning(error_message, len(non_existing_output))
            raise FileNotFoundError(error_message, len(non_existing_output))

        output_info = "\n\t".join(
            ["%s: %s" % (key, value) for key, value in return_status_dict.items()]
        )

        self.log.warning(
            "Managed %d returned jobs.\n\t%s",
            len(returned_jobs),
            output_info,
            "Managed %d returned jobs.\n\t%s",
            len(returned_jobs) + len(reset_jobs),
            output_info,
        )

        return returned_jobs, reset_jobs

    def restart_walltime_error_jobs(self, reset_jobs):

        reset_jobs_list = self.workModule.restart_jobs(reset_jobs, self.config_key)

        return reset_jobs_list

    def manage_finished_jobs(self, finished_jobs):
        """
        Manage the finished jobs by collecting the orca output data and performing connectivity checks.

        Args:
            finished_jobs (list): List of finished jobs.
        """
        if finished_jobs is None:
            return

        job_slurm_ids = {}

        for job in finished_jobs:
            # skip job if already collected.
            # This shouln't happen but is a safety measure
            if self.config_key in job.efficiency_data.keys():
                continue

            job_slurm_ids[job.slurm_id_per_key[self.config_key]] = job

        # collect the orca output data for all jobs

        for job in finished_jobs:

            self.workModule.collect_results(job, self.config_key)

            # if result_dict and result_dict["connectivity_check"] is False:
            #     self.log.warning("Connectivity check for %s was not successful!", job)
            # if result_dict and result_dict["connectivity_check"] is False:
            #     self.log.warning("Connectivity check for %s was not successful!", job)

        collection_format_arguments = [
            "JobID",
            "JobName",
            "ExitCode",
            "NCPUS",
            "CPUTimeRAW",
            "ElapsedRaw",
            "TimelimitRaw",
            "ConsumedEnergyRaw",
            "MaxDiskRead",
            "MaxDiskWrite",
            "MaxVMSize",
            "ReqMem",
            "MaxRSS",
        ]
        if not job_slurm_ids:
            return

        slurm_df = self._get_slurm_sacct_output(
            job_slurm_ids.keys(), collection_format_arguments
        )

        for slurm_id, job in job_slurm_ids.items():
            slurm_job = slurm_df[
                slurm_df["JobID"]
                .astype(str)
                .str.contains(f"{slurm_id}|{slurm_id}.batch|{slurm_id}.extern")
            ]
            if slurm_job.empty:
                continue

            slurm_job_dict = slurm_job.to_dict(orient="list")
            job.efficiency_data[self.config_key] = self._filter_data(slurm_job_dict)

    async def loop(self):
        """
        Executes the main loop for the work manager.

        This method continuously checks the status of jobs, prepares and submits new jobs,
        and manages completed or failed jobs until all jobs are done or the maximum number
        of loops is reached.

        Returns:
            bool: True if all jobs are done, False otherwise.
        """

        def all_jobs_done(current_job_dict):

            # because the dict is not cleared after each step
            # it will only be empty one iteration after all jobs are done
            total_jobs_remaining = (
                len(current_job_dict["not_found"])
                + len(current_job_dict["found"])
                + len(current_job_dict["not_started"])
                + len(current_job_dict["submitted"])
                + len(current_job_dict["returned"])
            )

            log_dict = "\n\t".join(
                [f"{key}: {len(value)}" for key, value in current_job_dict.items()]
            )

            self.log.info(
                f"Total jobs overview: {total_jobs_remaining} \n\t"
                + log_dict
                + f"\n\t {total_jobs_remaining} remaining."
            )
            self.log.debug(current_job_dict)
            return total_jobs_remaining == 0

        n_loops = 0
        # this loop will break if all jobs are done
        while True:
            n_loops += 1

            # current_job_dict
            #  not_assigned,found, not_started, submitted,returned, finished, failed

            # check current status of all jobs
            current_job_dict = self.check_job_status()

            # prepare jobs
            current_job_dict["not_started"].extend(
                self.prepare_jobs(current_job_dict["found"])
            )

            # submit jobs
            current_job_dict["submitted"].extend(
                self.submit_jobs(current_job_dict["not_started"])
            )

            # check on submitted jobs
            current_job_dict["returned"].extend(
                self.check_submitted_jobs(current_job_dict["submitted"])
            )

            # manage finished jobs
            fresh_finished, reset_jobs = self.manage_returned_jobs(
                current_job_dict["returned"]
            )

            # restart walltime error jobs
            # will be resubmitted in the next loop
            current_job_dict["restarted_jobs"] = self.restart_walltime_error_jobs(
                reset_jobs
            )

            # check on newly finished jobs to collect efficiency data
            self.manage_finished_jobs(fresh_finished)

            if all_jobs_done(current_job_dict):
                break

            # time.sleep(self.wait_time)
            await asyncio.sleep(self.wait_time)

            if self.max_loop > 0 and n_loops >= self.max_loop:
                self.log.info(f"Breaking loop after {n_loops}.")

                return f"Breaking loop after {n_loops}."

        self.log.info(f"All jobs done after {n_loops}.")
        self.is_finished = True
        return f"All jobs done after {n_loops}."

    def _convert_order_of_magnitude(self, value):

        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)

        if "K" in value:
            scaling = 1000
        elif "M" in value:
            scaling = 1000000
        elif "G" in value:
            scaling = 1000000000
        elif "T" in value:
            scaling = 1000000000000
        elif "P" in value:
            scaling = 1000000000000000
        else:
            scaling = 1

        try:
            new_value = float(value[:-1]) * scaling
        except ValueError:
            if int(value) == 0:
                new_value = 0.0
        return new_value

    def _filter_data(self, data):

        ureg = self.ureg
        filtered_data = {}

        for key, value in data.items():
            if value[0] == [""] and value[1] == [""]:
                filtered_data[key] = "Missing"
                continue

            if key == "JobID":
                filtered_data[key] = value[0]
            elif key == "JobName":
                filtered_data[key] = value[0]
            elif key == "ExitCode":
                filtered_data[key] = value[0]
            elif key == "NCPUS":
                filtered_data[key] = value[0]
            elif key == "CPUTimeRAW":
                filtered_data[key] = float(value[0]) * ureg.second
            elif key == "ElapsedRaw":
                filtered_data[key] = float(value[0]) * ureg.second
            elif key == "TimelimitRaw":
                filtered_data[key] = float(value[0]) * ureg.minute
            elif key == "ConsumedEnergyRaw":
                filtered_data[key] = float(value[1]) * ureg.joule
            elif key == "MaxDiskRead":
                filtered_data[key] = (
                    self._convert_order_of_magnitude(value[1]) * ureg.byte
                )
            elif key == "MaxDiskWrite":
                filtered_data[key] = (
                    self._convert_order_of_magnitude(value[1]) * ureg.byte
                )
            elif key == "MaxVMSize":
                filtered_data[key] = (
                    self._convert_order_of_magnitude(value[1]) * ureg.byte
                )
            elif key == "ReqMem":
                filtered_data[key] = (
                    self._convert_order_of_magnitude(value[0]) * ureg.byte
                )
            elif key == "maxRamUsage":
                filtered_data[key] = (
                    self._convert_order_of_magnitude(value[1]) * ureg.byte
                )
        return filtered_data
