import logging
import shutil


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

        found_xyz_files = list(self.input_dir.glob("*.xyz"))
        for file in found_xyz_files:
            file_stem = file.stem.split("_", maxsplit=1)[1]
            if file_stem in self.all_jobs_dict["not_yet_found"]:
                self.all_jobs_dict["not_yet_found"].remove(file_stem)

        self.all_jobs_dict["not_yet_prepared"] += found_xyz_files
        self.log.info(f"Found {len(found_xyz_files)} new xyz files.")

    def check_output_dir(self):
        pass

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

        self.all_jobs_dict["not_yet_submitted"] = []
        self.post_submit_cleanup()

    def post_submit_cleanup(self):
        """
        Archive up the input dir after submission.
        Delete now archived input files.
        """
        for job_dir in self.all_jobs_dict["submitted"]:
            shutil.make_archive(
                job_dir.parents[0] / ("archive_" + str(job_dir.stem)),
                "zip",
                job_dir,
            )
            shutil.rmtree(job_dir)

    def check_completed_job_status(self):
        """
        Check if a job was succesfull and if not try to find out what the cause was.

        """
        pass

    def manage_failed_jobs(self):

        pass

    def manage_finished_jobs(self):
        pass

    def loop(self):
        pass
