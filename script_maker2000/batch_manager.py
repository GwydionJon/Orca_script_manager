from collections import defaultdict
import asyncio
import logging
import itertools
import json
from pathlib import Path
from tqdm import tqdm
import traceback
import zipfile

from script_maker2000.files import (
    read_config,
    create_working_dir_structure,
    read_mol_input_json,
    add_dir_to_config,
    change_entry_in_batch_config,
)
from script_maker2000.work_manager import WorkManager
from script_maker2000.orca import OrcaModule
from script_maker2000.job import Job


class BatchManager:
    """This class is the main implementation for reading config files,
    organizing the file structure and starting the work managers.
    """

    def __init__(
        self,
        main_config_path,
        override_continue_job=False,
        show_current_job_status=True,
    ) -> None:

        if not isinstance(main_config_path, str) and not isinstance(
            main_config_path, Path
        ):
            raise TypeError(
                f"main_config_path should be a string, not {type(main_config_path)}."
            )
        if Path(main_config_path).is_dir():
            main_config_path = Path(main_config_path) / "example_config.json"

        self.main_config = self.read_config(
            main_config_path, override_continue_job=override_continue_job
        )

        if self.main_config["main_config"]["continue_previous_run"] is False:
            # this is the default start of a new batch run
            (
                self.working_dir,
                self.new_input_path,
                self.new_json_file,
                self.all_input_files,
            ) = self.initialize_files()

            self.job_dict = self._jobs_from_initial_json(self.new_json_file)

            self.work_managers = self.setup_work_modules_manager()
            self.copy_input_files_to_first_work_manager()

        else:
            self.working_dir = Path(self.main_config["main_config"]["output_dir"])
            self.new_input_path = self.working_dir / "start_input_files"
            self.new_json_file = self.working_dir / "new_input.csv"
            input_json_file = self.working_dir / "job_backup.json"
            self.job_dict = self._jobs_from_backup_json(input_json_file)

            self.work_managers = self.setup_work_modules_manager()

        # parameter for loop
        self.wait_time = self.main_config["main_config"]["wait_for_results_time"]
        self.max_loop = -1  # -1 means infinite loop until all jobs are done
        self.show_current_job_status = show_current_job_status

        # set up logging for this module
        self.log = logging.getLogger("BatchManager")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler_log = logging.FileHandler(self.working_dir / "BatchManager.log")
        file_handler_log.setFormatter(formatter)

        self.log.addHandler(file_handler_log)

        self.log.setLevel("INFO")

    def read_config(self, main_config_path, override_continue_job):
        """
        Reads the main configuration file.

        Args:
            main_config_path (str): The path to the main configuration file.
            override_continue_job (bool): Whether to override the continue_previous_run flag in the main configuration.

        Returns:
            dict: The parsed main configuration.
        """
        return read_config(
            main_config_path, override_continue_job=override_continue_job
        )

    def initialize_files(self):
        """
        Initializes the files for batch processing.

        This method creates a working directory structure based on the main configuration,
        retrieves all input files from the new input path, and extracts the job IDs from
        the file names.

        Returns:
            tuple: A tuple containing the working directory path, the new input path,
            the input job IDs, the new CSV file path, and a list of all input files.
        """
        working_dir, new_input_path, new_json_file = create_working_dir_structure(
            self.main_config
        )
        all_input_files = list(new_input_path.glob("*[!csv]"))

        return working_dir, new_input_path, new_json_file, all_input_files

    def _jobs_from_initial_json(self, json_file_path):
        """
        Creates job objects from an initial JSON file.

        Args:
            json_file_path (str): The path to the initial JSON file.

        Returns:
            dict: A dictionary of job objects, where the keys are the unique job IDs.
        """
        input_mol_dict = read_mol_input_json(json_file_path)

        config_keys = list(self.main_config["loop_config"].keys())
        config_stages = defaultdict(list)
        for key in config_keys:
            config_stages[self.main_config["loop_config"][key]["step_id"]].append(key)

        # Sort the dictionary by keys and get the values
        values = [v for k, v in sorted(config_stages.items())]
        # Generate all combinations
        combinations = list(itertools.product(*values))

        jobs = []
        for combination in combinations:
            for job_id, job_entry in input_mol_dict.items():

                charge = job_entry["charge"]
                multiplicity = job_entry["multiplicity"]

                job = Job(job_id, combination, self.working_dir, charge, multiplicity)
                jobs.append(job)
        # search for jobs that have the same steps.

        if self.main_config["main_config"]["parallel_layer_run"]:
            for job1 in jobs:
                for job2 in jobs:

                    # test if jobs are elligible for overlap
                    if job1 == job2:
                        continue
                    if job1.mol_id != job2.mol_id:
                        continue

                    # test if they have overlapping pathways
                    for i in range(len(job1.all_keys)):
                        if job1.all_keys[:i] == job2.all_keys[:i] and job1.all_keys[:i]:

                            if job2 not in job1.overlapping_jobs:
                                job1.overlapping_jobs.append(job2)
                            if job1 not in job2.overlapping_jobs:
                                job2.overlapping_jobs.append(job1)

        job_dict = {job.unique_job_id: job for job in jobs}
        return job_dict

    def _jobs_from_backup_json(self, json_file_path):
        """
        Creates job objects from a backup JSON file.

        Args:
            json_file_path (str): The path to the backup JSON file.

        Returns:
            dict: A dictionary of job objects, where the keys are the unique job IDs.
        """
        # prepare all job ids
        job_dict = {}
        with open(json_file_path, "r", encoding="utf-8") as json_file:
            job_backup = json.load(json_file)

        for job_id_backup, job_dict_backup in tqdm(job_backup.items()):
            job_dict[job_id_backup] = Job.import_from_dict(
                job_dict_backup, self.working_dir
            )

        return job_dict

    def setup_work_modules_manager(self):
        """
        Sets up the work managers based on the main configuration.

        Returns:
            dict: A dictionary of work managers, where the keys are the step IDs.
        """
        work_managers = defaultdict(list)

        for key, value in self.main_config["loop_config"].items():
            if value["type"] == "orca":
                orca_module = OrcaModule(self.main_config, key)
                work_manager = WorkManager(orca_module, job_dict=self.job_dict)
                work_managers[work_manager.step_id].append(work_manager)

            elif value["type"] == "crest":
                pass  # this is not implemented yet
            else:
                raise NotImplementedError(
                    f"Work type {value['type']} is not implemented yet."
                    + "Currently only orca is supported. Feel free to implement it yourself :)."
                )
        return work_managers

    def copy_input_files_to_first_work_manager(self):
        """
        Copies input files to the input directory of the first work manager.
        """
        # find lowest valid step id
        id_list = []
        for work_manager_list in self.work_managers.values():
            for work_manager in work_manager_list:
                id_list.append(work_manager.step_id)
        self.min_step_id = min(id_list)
        self.max_step_id = max(id_list)

        for work_manager in self.work_managers[self.min_step_id]:
            work_manager.log.info(
                f"Copying input files to {work_manager.config_key} input dir."
            )
            work_key = work_manager.config_key
            for job in self.job_dict.values():
                if job.check_status_for_key(work_key) == "not_assigned":
                    continue

                for file in self.all_input_files:
                    if job.mol_id in file.stem:
                        job.prepare_initial_job(work_key, self.min_step_id, file)

    def advance_jobs(self):
        """
        Advances all jobs to the next step.
        """
        advancement_dict = defaultdict(lambda: 0)
        for job in self.job_dict.values():
            advancement_output = job.advance_to_next_key()
            advancement_dict[advancement_output] += 1

        log_message = "Advancement dict: "
        for key, value in advancement_dict.items():
            log_message += f"{key}: {value} "

        self.log.info(log_message)

    def start_work_manager_loops(self):
        """
        Starts the work manager loops with threading.

        Returns:
            set: A set of manager tasks.
        """
        manager_runs = set()
        for work_managers_list in self.work_managers.values():
            for work_manager in work_managers_list:
                task = asyncio.create_task(
                    work_manager.loop(), name=work_manager.config_key
                )
                manager_runs.add(task)

        return manager_runs

    def save_current_jobs(self):
        """
        Saves the current jobs to a backup JSON file.
        """
        job_backup = {}
        for job in self.job_dict.values():
            job_backup[job.unique_job_id] = job.export_as_dict()

        with open(
            self.working_dir / "job_backup.json", "w", encoding="utf-8"
        ) as json_file:
            json.dump(job_backup, json_file, indent=4)

    async def batch_processing_loop(self):
        """
        Sets up the main batch processing loop and runs it until all tasks are done.

        Returns:
            set: A set of manager tasks.
        """
        manager_tasks = self.start_work_manager_loops()
        self.log.info(f"Background tasks first: {manager_tasks}")

        i = 1
        while True:
            self.advance_jobs()
            self.save_current_jobs()
            i += 1

            if all([task.done() for task in manager_tasks]):
                self.log.info(f"All tasks done after {i} loops")
                break

            if i > self.max_loop and self.max_loop > 0:
                self.log.info(f"Breaking main loop after{self.max_loop}.")
                break

            await asyncio.sleep(self.wait_time)
            if self.show_current_job_status:
                self.collect_current_job_status()
        return manager_tasks

    def collect_current_job_status(self):

        status_dict = defaultdict(lambda: 0)

        for job in self.job_dict.values():
            status = job.current_status
            status_dict[status] += 1
            for key, status in job.status_per_key.items():
                if key != job.current_key:
                    status_dict[status] += 1

        progress_msg = "Current jobs status: "
        # possible states are: submitted, failed, finished
        for status in ["submitted", "failed", "finished"]:
            num = status_dict.get(status, 0)
            progress_msg += f"{status}: {num:06d}, "

        print(progress_msg, end="\r", flush=True)

    def collect_result_overview(self):
        """
        Collects the result overview of the jobs.
        """
        status_dict = defaultdict(lambda: 0)
        failed_set = set()
        for job in self.job_dict.values():

            if job.current_status == "failed":
                status_dict[job.failed_reason] += 1
                failed_set.add(job.failed_reason)

            status_dict[job.current_status] += 1

        log_message = "Status overview: \n"
        for status, num in status_dict.items():
            if status in failed_set:
                log_message += f"\t{num} jobs failed with {status} \n"
            elif status == "failed":
                log_message += f"\t{num} jobs failed in total. \n"
            else:
                log_message += f"\t{num} jobs with {status} \n"
        self.log.info(log_message)
        return status_dict

    def create_config_entry(self):
        """Create a config entry for the current batch run."""

        result_str = add_dir_to_config(
            self.working_dir,
        )

        if "already exists" in result_str:
            error_msg = f"Working dir {self.working_dir} does already exists for config {self.config_name}.\n"
            error_msg += " Please make sure to choose a unique combination."

            self.log.error(error_msg)
            raise ValueError(error_msg)

    def finish_config_entry(self):

        change_entry_in_batch_config(
            config_name=self.main_config["main_config"]["config_name"],
            new_status="finished",
            output_dir=self.working_dir,
        )

    def run_batch_processing(self, supress_exceptions=False):
        """
        Starts the batch processing loop and returns the results.
        It will block until all tasks are done.
        This is the main working loop.
        """

        # create config entry right before starting the loop
        self.create_config_entry()

        task_results = asyncio.run(self.batch_processing_loop())
        result_dict = self.collect_result_overview()

        # create a zip ball of the output directory

        output_filename = self.working_dir / f"{self.working_dir.stem}.zip"
        source_dir = Path(self.working_dir)

        # Find all subfolders and files
        all_files = list(source_dir.glob("**/*"))

        with zipfile.ZipFile(output_filename, "w") as zipf:
            for file in all_files:
                if file.is_file():  # Only add files, not directories
                    zipf.write(
                        str(file),
                        str(file.relative_to(source_dir)),
                    )

        # check tasks for errors:
        exit_code = 0
        all_errors = []
        all_error_tasks = []
        all_error_traceback = []

        for task in task_results:
            try:
                self.log.info(task.result())
            except FileNotFoundError as e:
                if e:
                    exit_code = 1
                    all_errors.append(e)
                    all_error_traceback.append(traceback.format_exc())
                    all_error_tasks.append(task)
            except asyncio.CancelledError as e:
                if e:
                    exit_code = 1
                    all_errors.append(e)
                    all_error_traceback.append(traceback.format_exc())
                    all_error_tasks.append(task)

            except Exception as e:
                if e:
                    exit_code = 1
                    all_errors.append(e)
                    all_error_traceback.append(traceback.format_exc())
                    all_error_tasks.append(task)

        # finish config entry
        self.finish_config_entry()

        if exit_code == 1:
            self.log.error(
                f"There was an error in the batch processing loop in task {all_error_tasks}."
                + f"Errors: {all_errors} \n \n"
                + f"Adding Traceback: {all_error_traceback}"
            )
            if not supress_exceptions:
                raise RuntimeError(
                    f"There was an error in the batch processing loop in task {all_error_tasks}."
                    + f"Errors: {all_errors}"
                    + f"Adding Traceback: {all_error_traceback}"
                )

        if "failed" in result_dict.keys():
            exit_code = 1
            self.log.error("Jobs have failed, please check log. Exiting with code 1.")

            if not supress_exceptions:
                raise RuntimeError(
                    "Jobs have failed, please check status overview in log. "
                    + "See job_backup.json for more detailed information per job. Exiting with code 1. "
                )
        else:
            self.log.info(f"Batch processing loop finished with exit code {exit_code}.")

        return exit_code, task_results
