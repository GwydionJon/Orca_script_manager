import logging
import time
import shutil
from pathlib import Path
import asyncio
import subprocess


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
        self.config_key = self.workModule.config_key
        self.module_config = WorkModule.internal_config
        self.log = logging.getLogger(self.workModule.config_key)

        self.input_dir = self.workModule.working_dir / "input"
        self.output_dir = self.workModule.working_dir / "output"
        self.finished_dir = self.workModule.working_dir / "finished"
        self.failed_dir = self.workModule.working_dir / "failed"

        self.all_jobs_dict = {
            "not_yet_found": all_job_ids,
            "not_yet_prepared": [],
            "not_yet_submitted": [],
            "submitted": [],
            "submitted_ids_files": {},  # job_dir:job_id
            "returned_jobs": [],
            "finished": [],
            "walltime_error": [],
            "missing_ram_error": [],
            "unknown_error": [],
        }
        self.n_total_jobs = len(all_job_ids)
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

    def check_input_dir(self):
        """
        Checks the input directory for new XYZ files and updates the job status accordingly.

        This method searches for XYZ files in the input directory and updates the job status
        based on the files found. It removes the job ID from the "not_yet_found" list if the
        corresponding XYZ file is found. It adds the found XYZ files to the "not_yet_prepared"
        list. Finally, it logs the number of new XYZ files found.

        Returns:
            None
        """
        found_xyz_files = list(self.input_dir.glob("*.xyz"))
        for file in found_xyz_files:
            # split at first _ to get the job id
            file_stem = file.stem.split("___", maxsplit=1)[1]
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
            process = self.workModule.run_job(job_dir)
            job_id = int(process.stdout.split("job ")[1])
            self.all_jobs_dict["submitted"].append(job_dir)
            self.all_jobs_dict["submitted_ids_files"][job_dir.stem] = job_id

            time.sleep(0.3)
        self.all_jobs_dict["not_yet_submitted"] = []

    def check_slurm_status(self, id) -> bool:
        process = subprocess.run(
            [shutil.which("sacct"), "-j", f"{id}", "-o", "state"],
            shell=False,
            check=False,
            capture_output=True,  # Python >= 3.7 only
            text=True,  # Python >= 3.7 only
            # shell = False is important on justus
        )
        process_out = process.stdout
        process_out = " ".join(process_out.split())
        if "COMPLETED" in process_out:
            return True
        else:
            return False

    def check_output_dir(self):
        """find new jobs in output dir and check if they are finished."""
        output_dirs = list(self.output_dir.glob("*"))
        for output_dir in output_dirs:

            if self.input_dir / output_dir.stem in self.all_jobs_dict["submitted"]:

                job_id = self.all_jobs_dict["submitted_ids_files"][output_dir.stem]
                # job is only finished if slurm says so
                print(self.check_slurm_status(job_id))
                if self.check_slurm_status(job_id):
                    print("should remove")
                    self.all_jobs_dict["submitted"].remove(
                        self.input_dir / output_dir.stem
                    )
                    self.all_jobs_dict["returned_jobs"].append(output_dir)

    def cleanup(self, job_out_dir: Path):
        # archive input files
        shutil.make_archive(
            self.input_dir / ("archive_" + str(job_out_dir.stem)),
            "gztar",
            self.input_dir,
            job_out_dir.stem,
        )
        shutil.make_archive(
            job_out_dir.parents[0] / ("archive_" + str(job_out_dir.stem)),
            "gztar",
            job_out_dir.parents[0],
            job_out_dir.stem,
            verbose=True,
        )

        # remove input files
        shutil.rmtree(self.input_dir / job_out_dir.stem)
        shutil.rmtree(job_out_dir)

    def manage_file_names(self, job_out_dir):
        """Geberate new job out dir name and change all file names accordingly.

        Returns:
            _type_: _description_
        """
        label_id_split = "___"
        label_split = "__"
        # test if START_ is in label, if so delete it
        # if "START" == job_out_dir.name.split("___", 1)[0]:
        #    old_label = job_out_dir.name.split("___", 1)[0]
        # else:
        old_label = job_out_dir.name.split(label_id_split, 1)[0]

        new_label = self.workModule.config_key.upper()

        complete_label = old_label + label_split + new_label + label_id_split

        # create new job out dir
        new_job_out_dir = str(job_out_dir).replace(
            old_label + label_id_split, complete_label
        )
        new_job_out_dir = Path(new_job_out_dir)

        # new_job_out_dir.mkdir(parents=True, exist_ok=True)

        # rename all files in job_out_dir
        for file in job_out_dir.glob("*"):

            new_file_name = file.parents[0] / str(file.name).replace(
                old_label + label_id_split, complete_label
            )
            file.rename(new_file_name)

        # remove old dir
        # shutil.rmtree(job_out_dir)

        return new_job_out_dir

    def check_completed_job_status(self):
        """
        Check if a job was succesfull and if not try to find out what the cause was.
        # TODO: implement a method to handle failed slurm jobs
        """
        new_finished = 0
        new_walltime_error = 0
        new_missing_ram_error = 0
        new_unknown_error = 0

        for job_out_dir in self.all_jobs_dict["returned_jobs"]:
            job_status = self.workModule.check_job_status(job_out_dir)

            # rename finished files when moving them to finished dir or failed dir
            # this should ensure that one can easily check which previous stages were done on this file

            new_job_out_dir = self.manage_file_names(job_out_dir)

            if job_status == "all_good":
                new_finished += 1
                self.all_jobs_dict["finished"].append(new_job_out_dir)
                target_dir = Path(
                    self.workModule.working_dir
                    / "finished"
                    / "raw_results"
                    / new_job_out_dir.stem,
                )
                target_dir.mkdir(parents=True, exist_ok=True)

            elif job_status == "walltime_error":
                new_walltime_error += 1
                self.all_jobs_dict["walltime_error"].append(job_out_dir)

                target_dir = Path(
                    self.workModule.working_dir
                    / "failed"
                    / ("WALLTIME-" + str(new_job_out_dir.stem))
                )

            elif job_status == "missing_ram_error":
                new_missing_ram_error += 1
                self.all_jobs_dict["missing_ram_error"].append(new_job_out_dir)

                target_dir = Path(
                    self.workModule.working_dir
                    / "failed"
                    / ("RAM-" + str(new_job_out_dir.stem))
                )

            else:
                new_unknown_error += 1
                self.all_jobs_dict["unknown_error"].append(new_job_out_dir)
                target_dir = Path(
                    self.workModule.working_dir
                    / "failed"
                    / ("ERROR-" + str(new_job_out_dir.stem))
                )

            shutil.copytree(job_out_dir, target_dir, dirs_exist_ok=True)
            # use old job_out_dir for cleanup
            self.cleanup(job_out_dir)

        self.log.info(
            f"From {len(self.all_jobs_dict['returned_jobs'])} returned jobs: "
            + f"{new_finished} finished normaly, {new_walltime_error} walltime errors,"
            + f" {new_missing_ram_error} missing ram errors, {new_unknown_error} unknown errors."
        )
        self.all_jobs_dict["returned_jobs"] = []

    def manage_failed_jobs(self):
        # TODO: implement a method to handle failed jobs
        # restart with more ram or longer walltime/ start from intermediate structure
        pass

    async def loop(self):
        """
        Executes the main loop for the work manager.

        This method continuously checks the status of jobs, prepares and submits new jobs,
        and manages completed or failed jobs until all jobs are done or the maximum number
        of loops is reached.

        Returns:
            bool: True if all jobs are done, False otherwise.
        """

        def all_jobs_done():

            total_jobs_remaining = (
                len(self.all_jobs_dict["not_yet_found"])
                + len(self.all_jobs_dict["not_yet_prepared"])
                + len(self.all_jobs_dict["not_yet_submitted"])
                + len(self.all_jobs_dict["submitted"])
                + len(self.all_jobs_dict["returned_jobs"])
            )

            self.log.info(f"Total jobs remaining: {total_jobs_remaining}")
            return total_jobs_remaining == 0

        n_loops = 0
        while not all_jobs_done():
            self.check_input_dir()
            self.prepare_jobs()
            self.submit_jobs()

            # this should catch submission errors
            time.sleep(3)

            self.check_output_dir()
            self.check_completed_job_status()
            self.manage_failed_jobs()

            if all_jobs_done():
                break

            # time.sleep(self.wait_time)
            await asyncio.sleep(self.wait_time)

            n_loops += 1
            if self.max_loop > 0 and n_loops >= self.max_loop:
                self.log.info(f"Breaking loop after {n_loops}.")

                return f"Breaking loop after {n_loops}."
        self.log.info(f"All jobs done after {n_loops}.")
        self.is_finished = True
        return f"All jobs done after {n_loops}."
