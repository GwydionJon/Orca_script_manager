from collections import OrderedDict
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

        work_managers = OrderedDict()

        for key, value in self.main_config["loop_config"].items():
            if value["type"] == "orca":
                orca_module = OrcaModule(self.main_config, key, input_df=self.input_df)
                work_manager = WorkManager(
                    orca_module, all_job_ids=self.all_job_ids.copy()
                )
                work_managers[key] = work_manager
            elif value["type"] == "crest":
                pass  # this is not implemented yet
            else:
                raise NotImplementedError(
                    f"Work type {value['type']} is not implemented yet."
                    + "Currently only orca is supported. Feel free to implement it yourself :)."
                )
        return work_managers

    def copy_input_files_to_first_work_manager(self):
        first_manager = list(self.work_managers.values())[0]
        shutil.copytree(
            self.new_input_path, first_manager.input_dir, dirs_exist_ok=True
        )

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
        for work_key, work_manager in self.work_managers.items():
            # work_manager.manage_failed_jobs()

            for status_key, job_list in work_manager.all_jobs_dict.items():
                if "_error" in status_key:
                    job_ids = [error.stem.split("_", 1)[1] for error in job_list]

                    if job_ids:
                        # Update the status of the failed jobs in the input dataframe
                        self.input_df.loc[job_ids, work_key] = status_key

                        # Get all following work keys and set status to cancelled
                        following_work_keys = list(
                            self.main_config["loop_config"].keys()
                        )[
                            list(self.main_config["loop_config"].keys()).index(work_key)
                            + 1 :
                        ]

                        for following_key in following_work_keys:
                            # Remove the failed jobs from the expected input in the following work managers
                            self.work_managers[following_key].log.info(
                                f"Removing {len(job_ids)} jobs from expected input due to {status_key}."
                            )
                            self.input_df.loc[job_ids, following_key] = "cancelled"

                            # Remove the failed jobs from the lists of following work managers
                            for id_ in job_ids:
                                if (
                                    id_
                                    in self.work_managers[following_key].all_jobs_dict[
                                        "not_yet_found"
                                    ]
                                ):
                                    self.work_managers[following_key].all_jobs_dict[
                                        "not_yet_found"
                                    ].remove(id_)

        # Save the updated input dataframe to the new csv file
        self.input_df.to_csv(self.new_csv_file)

    def manage_job_logging(self):

        # failed jobs are handled in manage_failed_jobs
        # then manage all other jobs
        for work_key, work_manager in self.work_managers.items():
            for status_key, job_list in work_manager.all_jobs_dict.items():
                if "_error" not in status_key and status_key not in [
                    "not_yet_found",
                    "submitted_ids_files",
                ]:
                    job_ids = [error.stem.split("_", 1)[1] for error in job_list]
                    if job_ids:
                        self.input_df.loc[job_ids, work_key] = status_key

        self.input_df.to_csv(self.new_csv_file)

    def move_files(self):
        for i, (key, work_manager) in enumerate(self.work_managers.items()):

            work_manager_finished_dir = work_manager.finished_dir
            # skip if work manager is finished

            if i == len(self.work_managers) - 1:  # -1 because of 0 indexing
                # move files from last work manager to finished folder

                print("Test")
                target_files = list(work_manager_finished_dir.glob("*"))
                print(work_manager_finished_dir)
                print(target_files)
                target_dir = self.working_dir / "finished" / "raw_results"

            else:
                # move files from current work manager to next work manager

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
                    continue

                next_work_manager = list(self.work_managers.values())[i + 1]

                # check which jobs from finished dir have not yet been submitted to the next worker
                target_files = []
                for potential_target_file in potential_target_files:
                    job_id = potential_target_file.stem.split("_", 1)[1]
                    if job_id in next_work_manager.all_jobs_dict["not_yet_found"]:
                        target_files.append(potential_target_file)

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
        for work_manager in self.work_managers.values():
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
