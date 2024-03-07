import logging
import time


class WorkManager:

    def __init__(self, WorkModule, all_job_ids) -> None:
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
        self.module_config = WorkModule.internal_config
        self.log = logging.getLogger(self.workModule.config_key)

        self.input_dir = self.workModule.working_dir / "input"
        self.output_dir = self.workModule.working_dir / "output"

        self.all_jobs_dict = {
            "not_yet_found": all_job_ids,
            "not_yet_prepared": [],
            "not_yet_submitted": [],
            "submitted": [],
            "returned_jobs": [],
            "finished": [],
            "walltime_error": [],
            "missing_ram_error": [],
            "unknown_error": [],
        }
        self.finished_all_jobs = False

    # check input dir
    # check output dir
    # submit jobs
    # catch submit errors
    # check job status
    # manage failed jobs
    # manage finished jobs
    # loop
    # check if all jobs are done

    def check_input_dir(self):
        """Check the input dir for new xyz files."""

        found_xyz_files = list(self.input_dir.glob("*.xyz"))
        for file in found_xyz_files:
            # split at first _ to get the job id
            file_stem = file.stem.split("_", maxsplit=1)[1]
            if file_stem in self.all_jobs_dict["not_yet_found"]:
                self.all_jobs_dict["not_yet_found"].remove(file_stem)

        self.all_jobs_dict["not_yet_prepared"] += found_xyz_files
        self.log.info(f"Found {len(found_xyz_files)} new xyz files.")

    def prepare_jobs(self):
        if self.all_jobs_dict["not_yet_prepared"]:
            input_dir_dict = self.workModule.prepare_jobs(
                self.all_jobs_dict["not_yet_prepared"]
            )

            # move jobs to not_yet_submitted
            for key, job_dir in input_dir_dict.items():
                self.all_jobs_dict["not_yet_submitted"].append(job_dir)
                self.all_jobs_dict["not_yet_prepared"].remove(
                    job_dir.parents[0] / (key + ".xyz")
                )

    def submit_jobs(self):
        for job_dir in self.all_jobs_dict["not_yet_submitted"]:
            self.workModule.run_job(job_dir)
            self.all_jobs_dict["submitted"].append(job_dir)
            time.sleep(0.3)
        self.all_jobs_dict["not_yet_submitted"] = []

    def check_output_dir(self):
        """find new jobs in output dir"""
        output_dirs = list(self.output_dir.glob("*"))
        for output_dir in output_dirs:
            if self.input_dir / output_dir.stem in self.all_jobs_dict["submitted"]:

                self.all_jobs_dict["submitted"].remove(self.input_dir / output_dir.stem)
                self.all_jobs_dict["returned_jobs"].append(output_dir)

    def check_completed_job_status(self):
        """
        Check if a job was succesfull and if not try to find out what the cause was.

        """
        new_finished = 0
        new_walltime_error = 0
        new_missing_ram_error = 0
        new_unknown_error = 0

        for jobb_out_dir in self.all_jobs_dict["returned_jobs"]:
            job_status = self.workModule.check_job_status(jobb_out_dir)
            if job_status == "all_good":
                new_finished += 1
                self.all_jobs_dict["finished"].append(jobb_out_dir)

            elif job_status == "walltime_error":
                new_walltime_error += 1
                self.all_jobs_dict["walltime_error"].append(jobb_out_dir)

            elif job_status == "missing_ram_error":
                new_missing_ram_error += 1
                self.all_jobs_dict["missing_ram_error"].append(jobb_out_dir)

            else:
                new_unknown_error += 1
                self.all_jobs_dict["unknown_error"].append(jobb_out_dir)
        self.log.info(
            f"From {len(self.all_jobs_dict['returned_jobs'])} returned jobs: "
            + f"{new_finished} finished normaly, {new_walltime_error} walltime errors,"
            + f" {new_missing_ram_error} missing ram errors, {new_unknown_error} unknown errors."
        )
        self.all_jobs_dict["returned_jobs"] = []

    def manage_failed_jobs(self):

        pass

    def manage_finished_jobs(self):
        pass

    def loop(self):
        pass
