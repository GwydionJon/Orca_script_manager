import logging


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
            "not_yet_submitted": [],
            "submitted": [],
            "finished": [],
            "failed": [],
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

        found_files = list(self.input_dir.glob("*xyz"))

        for file in found_files:
            file_stem = file.stem.split("_", maxsplit=1)[1]
            if file_stem in self.all_jobs_dict["not_yet_found"]:
                self.all_jobs_dict["not_yet_found"].remove(file_stem)

        self.all_jobs_dict["not_yet_submitted"] += found_files
        self.log.info(f"Found {len(found_files)} new jobs.")

    def check_output_dir(self):
        pass

    def submit_jobs(self):
        pass

    def check_completed_job_status(self):
        """
        Check if a job was succesfull and if not try to find out what the cause was.

        """

    def manage_failed_jobs(self):

        pass

    def manage_finished_jobs(self):
        pass

    def loop(self):
        pass
