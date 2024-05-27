"""
This module is intended to be used as a template class and provides necessary functions
for another module to be properly useful in the scope of this program.
"""

from pathlib import Path
import logging
from typing import Union
from script_maker2000.files import read_config
from abc import abstractmethod


class TemplateModule:
    """
    This class is only used as a template guide to have all derived classes follow the same general layout.
    """

    def __init__(
        self,
        main_config: dict,
        config_key: str,
    ) -> None:
        """
        Initializes the TemplateModule object.

        Args:
            main_config (dict): The main config file.
            config_key (str): The loop_config key this object is handling.

        Raises:
            NotImplementedError: This is just a template.
        """
        # please default to these naming conventions:

        if isinstance(main_config, Path):
            main_config = read_config(main_config, perform_validation=False)
        self.main_config = main_config
        self.config_key = config_key
        self.internal_config = self.create_internal_config(main_config, config_key)
        self.working_dir = (
            Path(main_config["main_config"]["output_dir"]) / "working" / config_key
        )

        # set up logging for this module
        self.log = logging.getLogger(self.config_key)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler_log = logging.FileHandler(self.working_dir / f"{config_key}.log")
        file_handler_log.setFormatter(formatter)

        self.log.addHandler(file_handler_log)

        self.log.setLevel("INFO")

    def create_internal_config(self, main_config, config_key) -> dict:
        """
        Extracts the necessary information from the main config and stores them.

        Returns:
            dict: A dict of the sub config.
        """
        internal_config = main_config["loop_config"][config_key]
        return internal_config

    @abstractmethod
    def create_slurm_scripts(self, slurm_config=None) -> Union[str, Path]:
        """
        Create the slurm script that is used to submit this calculation run to the server.
        This should use the slurm class provided in this module.
        """
        raise NotImplementedError

    @abstractmethod
    def prepare_jobs(self, input_dirs, **kwargs) -> dict:
        """
        Prepare the job files for submission.

        Args:
            input_files (list): List of input files.

        Returns:
            dict: A dict of the sub config.
        """
        raise NotImplementedError

    @abstractmethod
    def run_job(self, job) -> None:
        """
        Interface to send the job to the server.

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError

    @abstractmethod
    def restart_jobs(self, job_list, key):
        """
        Restart a job that failed.

        Args:
            job_list (list): List of jobs that failed.
            key (str): The key of the job that failed.
        """
        raise NotImplementedError

    @classmethod
    def collect_results(cls, job, key, results_dir="finished") -> dict:
        """
        Collect the results of the calculation and save in a {mol_id}_calc_result.json file in each subfolder.

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError

    @classmethod
    def check_job_status(cls, job) -> bool:
        """
        Provide some method to verify if a single calculation was successful.
        This should be handled independently from the existence of this class object.
        """
        raise NotImplementedError
