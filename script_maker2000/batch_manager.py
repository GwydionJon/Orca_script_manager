from collections import OrderedDict
import shutil

from script_maker2000.files import read_config, create_working_dir_structure
from script_maker2000.work_manager import WorkManager
from script_maker2000.orca import OrcaModule


class BatchManager:
    """This class is the main implementation for reading config files,
    organizing the file structure and starting the work managers.
    """

    def __init__(self, main_config_path) -> None:

        self.main_config = self.read_config(main_config_path)
        self.working_dir, self.new_input_path, self.all_job_ids = (
            self.initialize_files()
        )
        self.work_managers = self.setup_work_modules_manager()
        self.copy_input_files_to_first_work_manager()

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
        working_dir, new_input_path = create_working_dir_structure(self.main_config)
        all_input_files = list(new_input_path.glob("*[!csv]"))

        all_job_ids = [file.stem.split("START_")[1] for file in all_input_files]
        return working_dir, new_input_path, all_job_ids

    def setup_work_modules_manager(self):

        work_managers = OrderedDict()

        for key, value in self.main_config["loop_config"].items():
            if value["type"] == "orca":
                orca_module = OrcaModule(self.main_config, key)
                work_manager = WorkManager(orca_module, all_job_ids=self.all_job_ids)
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
    def start_work_managers(self):
        pass

    # TODO tell the work managers which jobs got cancelled so they can remove them from the list
    # otherwise they will never finish

    # maybe set them to failed and remove from the input list.
    # change total jobs number or come up with a different way to check if all jobs are done

    def move_files(self):
        for i, (key, work_manager) in enumerate(self.work_managers.items()):

            work_manager_finished_dir = work_manager.finished_dir

            if i == len(self.work_managers) - 1:  # -1 because of 0 indexing
                # move files from last work manager to finished folder
                target_files = list(work_manager_finished_dir.glob("*"))

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

                target_files = []
                for file_type in target_file_types:
                    target_files += list(
                        work_manager_finished_dir.glob(f"*/*{file_type}")
                    )

                next_work_manager = list(self.work_managers.values())[i + 1]
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
