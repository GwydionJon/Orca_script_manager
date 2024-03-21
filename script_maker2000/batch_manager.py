from collections import defaultdict
import asyncio
import pandas as pd
import time
import logging
import itertools
import json
from pathlib import Path

from script_maker2000.files import read_config, create_working_dir_structure
from script_maker2000.work_manager import WorkManager
from script_maker2000.orca import OrcaModule
from script_maker2000.job import Job


class BatchManager:
    """This class is the main implementation for reading config files,
    organizing the file structure and starting the work managers.
    """

    def __init__(self, main_config_path, override_continue_job=False) -> None:

        if Path(main_config_path).is_dir():
            main_config_path = Path(main_config_path) / "example_config.json"

        self.main_config = self.read_config(
            main_config_path, override_continue_job=override_continue_job
        )

        if self.main_config["main_config"]["continue_previous_run"] is False:
            (
                self.working_dir,
                self.new_input_path,
                self.input_job_ids,
                self.new_csv_file,
                self.all_input_files,
            ) = self.initialize_files()

            self.input_df = pd.read_csv(self.new_csv_file, index_col=0)
            self.input_df.set_index("key", inplace=True)
            self.job_dict = self._jobs_from_csv(self.input_df)

            self.work_managers = self.setup_work_modules_manager()
            self.copy_input_files_to_first_work_manager()
        else:
            self.working_dir = Path(self.main_config["main_config"]["output_dir"])
            self.new_input_path = self.working_dir / "start_input_files"
            self.new_csv_file = self.working_dir / "new_input.csv"
            input_json_file = self.working_dir / "job_backup.json"
            self.job_dict = self._jobs_from_backup_json(input_json_file)

            self.work_managers = self.setup_work_modules_manager()

        # parameter for loop
        self.wait_time = self.main_config["main_config"]["wait_for_results_time"]
        self.max_loop = -1  # -1 means infinite loop until all jobs are done

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
        working_dir, new_input_path, new_csv_file = create_working_dir_structure(
            self.main_config
        )
        all_input_files = list(new_input_path.glob("*[!csv]"))

        input_job_ids = [file.stem.split("START___")[1] for file in all_input_files]
        return working_dir, new_input_path, input_job_ids, new_csv_file, all_input_files

    def _jobs_from_csv(self, input_df):
        """
        Creates job objects from the input CSV file.

        Args:
            input_df (DataFrame): The input DataFrame.

        Returns:
            dict: A dictionary of job objects, where the keys are the unique job IDs.
        """
        input_job_ids = self.input_job_ids

        # get all stages and their config keys from the main config
        config_keys = list(self.main_config["loop_config"].keys())
        config_stages = defaultdict(list)
        for key in config_keys:
            config_stages[self.main_config["loop_config"][key]["step_id"]].append(key)

        # Sort the dictionary by keys and get the values
        values = [v for k, v in sorted(config_stages.items())]
        # Generate all combinations
        combinations = list(itertools.product(*values))

        # create a job for each combination of keys and input files
        jobs = []
        for combination in combinations:
            for job_id in input_job_ids:
                charge = input_df.loc[job_id, "charge"]
                multiplicity = input_df.loc[job_id, "multiplicity"]

                job = Job(job_id, combination, self.working_dir, charge, multiplicity)
                jobs.append(job)
        # search for jobs that have the same steps.
        #

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
        with open(json_file_path, "r") as json_file:
            job_backup = json.load(json_file)

        for job_id_backup, job_dict_backup in job_backup.items():
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
        times = []
        for work_managers_list in self.work_managers.values():
            for work_manager in work_managers_list:
                task = asyncio.create_task(
                    work_manager.loop(), name=work_manager.config_key
                )
                times.append(time.time())
                manager_runs.add(task)

        self.log.info(f"Time start all loops: {times[1]-times[0]} seconds.")

        return manager_runs

    def save_current_jobs(self):
        """
        Saves the current jobs to a backup JSON file.
        """
        job_backup = {}
        for job in self.job_dict.values():
            job_backup[job.unique_job_id] = job.export_as_dict()

        with open(self.working_dir / "job_backup.json", "w") as json_file:
            json.dump(job_backup, json_file)

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

        return manager_tasks

    def collect_result_overview(self):
        """
        Collects the result overview of the jobs.
        """
        status_dict = defaultdict(lambda: 0)
        for job in self.job_dict.values():
            status_dict[job.current_status] += 1

        log_message = "Status overview: "
        for key, value in status_dict.items():
            log_message += f"{key}: {value} "
        self.log.info(log_message)

    def run_batch_processing(self):
        """
        Starts the batch processing loop and returns the results.
        It will block until all tasks are done.
        This is the main working loop.
        """
        task_results = asyncio.run(self.batch_processing_loop())
        self.collect_result_overview()

        # check tasks for errors:
        exit_code = 0
        all_errors = []
        for task in task_results:
            try:
                self.log.info(task.result())
            except FileNotFoundError as e:
                if e:
                    exit_code = 1
                    all_errors.append(e)
            except asyncio.CancelledError as e:
                if e:
                    exit_code = 1
                    all_errors.append(e)
            except Exception as e:
                if e:
                    exit_code = 1
                    all_errors.append(e)

        if exit_code == 1:
            self.log.error(
                "There was an error in the batch processing loop."
                + f"Errors: {all_errors}"
            )
            raise RuntimeError(
                "There was an error in the batch processing loop."
                + f"Errors: {all_errors}"
            )
        return exit_code, task_results
