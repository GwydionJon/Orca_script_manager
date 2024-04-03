import logging
import asyncio
from collections import defaultdict
from script_maker2000.job import Job


class WorkManager:

    def __init__(self, WorkModule, job_dict: Job) -> None:
        """
        This class is used to manage the work of a WorkModule.
        For this it will check if new files are available,
          if so submit them to the server while keeping below the maximum number of jobs.
        It will also check if jobs are finished and handle the output files.
        Failed jobs will be collected and logged.

        Args:
            WorkModule (_type_): _description_
            n_total_jobs (_type_): _description_
        """

        self.main_config = WorkModule.main_config
        self.workModule = WorkModule
        self.job_dict = job_dict

        self.config_key = self.workModule.config_key
        self.module_config = WorkModule.internal_config
        self.step_id = self.module_config["step_id"]
        self.log = logging.getLogger(self.workModule.config_key)

        self.input_dir = self.workModule.working_dir / "input"
        self.output_dir = self.workModule.working_dir / "output"
        self.finished_dir = self.workModule.working_dir / "finished"
        self.failed_dir = self.workModule.working_dir / "failed"

        self.is_finished = False

        # this way the wait time can be adjusted with monkeypatch for faster testing
        self.wait_time = self.main_config["main_config"]["wait_for_results_time"]
        self.max_loop = -1  # -1 means infinite loop until all jobs are done
        # change max loop with monkeypatch for testing

    # check input dir
    # check output dir
    # submit jobs
    # catch submit errors
    # check job status
    # manage failed jobs
    # manage finished jobs
    # loop
    # check if all jobs are done

    def check_job_status(self):
        """Go over all jobs and check their status for this work manager."""

        current_job_dict = defaultdict(list)
        current_key = self.config_key
        for job_id, job in self.job_dict.items():
            status_result = job.check_status_for_key(current_key)
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

        for job in not_started_jobs:
            if job.current_status == "not_started":

                process = self.workModule.run_job(job.current_dirs["input"])
                job_id = int(process.stdout.split("job ")[1])
                job.slurm_id_per_key[self.config_key] = job_id
                job.current_status = "submitted"

        self.log.info(f"Submitted {len(not_started_jobs)} new jobs.")
        return not_started_jobs

    def check_submitted_jobs(self, submitted_jobs):
        """find new jobs in output dir and check if they have returned."""

        finished_jobs = []
        for job in submitted_jobs:
            if job.check_status_for_key(self.config_key) in ["returned", "failed"]:
                finished_jobs.append(job)
        self.log.info(f"Collected {len(finished_jobs)} returned jobs.")

        return finished_jobs

    def manage_returned_jobs(self, finished_jobs):

        # get job status from work module
        return_status_dict = defaultdict(lambda: 0)

        non_existing_output = []
        for job in finished_jobs:

            if job.current_dirs["output"].exists():
                work_module_status = self.workModule.check_job_status(
                    job.current_dirs["output"]
                )

            else:
                non_existing_output.append(job)

                continue

            return_status_dict[work_module_status] += 1

            job.manage_return(work_module_status)

        for job in non_existing_output:
            finished_jobs.remove(job)

        if non_existing_output:
            self.log.warning(
                f"Caught {len(non_existing_output)} non existing output dirs after slurm was finished."
                + f"\n\t{non_existing_output}"
            )
            raise FileNotFoundError(
                f"Caught {len(non_existing_output)} non existing output dirs after slurm was finished."
            )

        output_info = "\n\t".join(
            [f"{key}: {value}" for key, value in return_status_dict.items()]
        )

        self.log.info(f"Managed {len(finished_jobs)} returned jobs.\n\t" + output_info)

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
            self.manage_returned_jobs(current_job_dict["returned"])

            # # check on finished jobs job status
            # self.check_completed_job_status()
            # self.manage_failed_jobs()

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
