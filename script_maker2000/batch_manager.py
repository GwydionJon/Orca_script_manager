from collections import defaultdict
import shutil
import asyncio
import pandas as pd
import time
import logging
from script_maker2000.files import read_config, create_working_dir_structure
from script_maker2000.work_manager import WorkManager
from script_maker2000.orca import OrcaModule


class BatchManager:
    """This class is the main implementation for reading config files,
    organizing the file structure and starting the work managers.
    """

    def __init__(self, main_config_path) -> None:

        self.main_config = self.read_config(main_config_path)
        self.working_dir, self.new_input_path, self.all_job_ids, self.new_csv_file = (
            self.initialize_files()
        )

        self.input_df = pd.read_csv(self.new_csv_file, index_col=0)
        self.input_df.set_index("key", inplace=True)

        # add a column for each work step to the csv file
        for key in self.main_config["loop_config"].keys():
            self.input_df[key] = "not_yet_submitted"
        self.input_df.to_csv(self.new_csv_file)

        self.work_managers = self.setup_work_modules_manager()
        self.copy_input_files_to_first_work_manager()

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

    # only for initilization
    def read_config(self, main_config_path):
        return read_config(main_config_path)

    def initialize_files(self):
        """
        Initializes the files for batch processing.

        This method creates a working directory structure based on the main configuration,
        retrieves all input files from the new input path, and extracts the job IDs from
        the file names.

        Returns:
            working_dir (str): The path to the working directory.
            new_input_path (Path): The path to the new input files.
            all_job_ids (list): A list of job IDs extracted from the file names.
        """
        working_dir, new_input_path, new_csv_file = create_working_dir_structure(
            self.main_config
        )
        all_input_files = list(new_input_path.glob("*[!csv]"))

        all_job_ids = [file.stem.split("START_")[1] for file in all_input_files]
        return working_dir, new_input_path, all_job_ids, new_csv_file

    def setup_work_modules_manager(self):

        work_managers = defaultdict(list)

        for key, value in self.main_config["loop_config"].items():
            if value["type"] == "orca":
                orca_module = OrcaModule(self.main_config, key, input_df=self.input_df)
                work_manager = WorkManager(
                    orca_module, all_job_ids=self.all_job_ids.copy()
                )
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

        # find lowest valid step id
        id_list = []
        for work_manager_list in self.work_managers.values():
            for work_manager in work_manager_list:
                id_list.append(work_manager.step_id)
        self.min_step_id = min(id_list)
        self.max_step_id = max(id_list)
        for work_manager_list in self.work_managers.values():
            for work_manager in work_manager_list:
                if work_manager.step_id == self.min_step_id:
                    work_manager.log.info(
                        f"Copying input files to {work_manager.config_key} input dir."
                    )

                    shutil.copytree(
                        self.new_input_path, work_manager.input_dir, dirs_exist_ok=True
                    )
                    for file in list(work_manager.input_dir.glob("*")):
                        new_file = str(file).replace("START_", "START___")
                        file.rename(new_file)

    # end init

    # TODO tell the work managers which jobs got cancelled so they can remove them from the list
    # otherwise they will never finish

    # maybe set them to failed and remove from the input list.
    # change total jobs number or come up with a different way to check if all jobs are done

    def manage_failed_jobs(self):
        """
        This method manages the failed jobs by updating the status of the failed jobs in the input dataframe.
        It also cancels the jobs in the following work managers and removes the failed jobs from their lists.

        Returns:
            None
        """
        for step_id, work_manager_list in self.work_managers.items():
            for work_manager in work_manager_list:
                work_key = work_manager.config_key
                for status_key, job_list in work_manager.all_jobs_dict.items():
                    if "_error" in status_key:
                        job_ids = [error.stem.split("___", 1)[1] for error in job_list]

                        if job_ids:
                            # Update the status of the failed jobs in the input dataframe
                            self.input_df.loc[job_ids, work_key] = status_key

                            # Cancel the jobs in the following work managers and remove the failed jobs from their lists
                            for (
                                other_step_id,
                                other_work_manager_list,
                            ) in self.work_managers.items():
                                if other_step_id <= step_id:
                                    continue
                                for following_work_manager in other_work_manager_list:
                                    for id_ in job_ids:
                                        if (
                                            id_
                                            in following_work_manager.all_jobs_dict[
                                                "not_yet_found"
                                            ]
                                        ):
                                            following_work_manager.all_jobs_dict[
                                                "not_yet_found"
                                            ].remove(id_)

        # Save the updated input dataframe to the new csv file
        self.input_df.to_csv(self.new_csv_file)

    def manage_job_logging(self):

        # failed jobs are handled in manage_failed_jobs
        # then manage all other jobs
        for work_manager_list in self.work_managers.values():
            for work_manager in work_manager_list:
                work_key = work_manager.config_key
                for status_key, job_list in work_manager.all_jobs_dict.items():
                    if "_error" not in status_key and status_key not in [
                        "not_yet_found",
                        "submitted_ids_files",
                    ]:
                        job_ids = [error.stem.split("___", 1)[1] for error in job_list]
                        if job_ids:
                            self.input_df.loc[job_ids, work_key] = status_key

        self.input_df.to_csv(self.new_csv_file)

    def _find_target_files(self, work_manager_finished_dir, key, work_step_id):
        # setup target files
        target_file_types = [
            self.main_config["main_config"]["common_input_files"],
        ]
        if self.main_config["loop_config"][key]["additional_input_files"]:
            target_file_types.append(
                self.main_config["loop_config"][key]["additional_input_files"]
            )
        # collect all files in finished dir
        potential_target_files = []
        for file_type in target_file_types:
            potential_target_files += list(
                work_manager_finished_dir.glob(f"*/*{file_type}")
            )

        if not potential_target_files:
            return {}

        next_work_managers_list = self.work_managers[work_step_id + 1].copy()
        next_work_manager_dict = {}
        for next_work_manager in next_work_managers_list:
            # check which jobs from finished dir have not yet been submitted to the next worker
            target_files = []
            for potential_target_file in potential_target_files:
                job_id = potential_target_file.stem.split("___", 1)[1]
                if job_id in next_work_manager.all_jobs_dict["not_yet_found"]:
                    target_files.append(potential_target_file)
                next_work_manager_dict[next_work_manager] = target_files
        return next_work_manager_dict

    def move_files(self):
        for work_step_id, work_manager_list in self.work_managers.items():
            for work_manager in work_manager_list:

                key = work_manager.config_key
                work_manager_finished_dir = work_manager.finished_dir / "raw_results"

                # the last steps should copy their output directly in the finished dir
                if work_step_id == self.max_step_id:
                    # move files from last work manager to finished folder
                    target_files = list(work_manager_finished_dir.glob("*"))
                    target_dir = self.working_dir / "finished" / "raw_results"
                    for file in target_files:
                        if file.is_dir():
                            shutil.copytree(file, target_dir / file.name)
                        elif file.is_file():
                            shutil.copy(file, target_dir / file.name)

                else:
                    # move files from current work manager to next work manager
                    next_work_manager_dict = self._find_target_files(
                        work_manager_finished_dir, key, work_step_id
                    )
                    for (
                        next_work_manager,
                        target_files,
                    ) in next_work_manager_dict.items():
                        target_name = next_work_manager.config_key
                        work_manager.log.info(
                            f"Moving {len(target_files)} files to {target_name} input"
                        )

                        target_dir = next_work_manager.input_dir

                        for file in target_files:
                            if file.is_dir():
                                shutil.copytree(file, target_dir / file.name)
                            elif file.is_file():
                                shutil.copy(file, target_dir / file.name)

    def start_work_manager_loops(self):
        # start work manager loops with threading
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

    async def batch_processing_loop(self):
        """This sets up the main batch processing loop and runs it until all tasks are done.

        Returns:
            _type_: _description_
        """
        manager_runs = self.start_work_manager_loops()
        self.log.info(f"Background tasks first: {manager_runs}")

        i = 1
        while True:
            self.move_files()
            self.manage_failed_jobs()
            self.manage_job_logging()

            i += 1

            if all([task.done() for task in manager_runs]):
                self.log.info(f"All tasks done after {i} loops")
                break

            if i > self.max_loop and self.max_loop > 0:
                self.log.info("Breaking main loop after 10.")
                break

            await asyncio.sleep(self.wait_time)

        return manager_runs

    def run_batch_processing(self):
        """This function will start the batch processing loop and return the results.
            It will block until all tasks are done.
            This is the main working loop.

        Returns:
            _type_: _description_
        """
        return asyncio.run(self.batch_processing_loop())
