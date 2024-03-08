# this module is onlz intendet to be used as a template class and provides necessary function
# for another module to be properly useful in the scope of this program.
from pathlib import Path
import logging
from script_maker2000.files import read_config


class TemplateModule:

    def __init__(self, main_config: dict, config_key: str) -> None:
        """
        This class is only used as a template guide to have all derived classes follow the same generell layout.


        The init should handle the setup process.
        This includes setting up any necessary files (slurm script etc.)

        In addition to these functions you can use any number of helper functions, as long as they are contained within.

        Args:
            main_config (dict): The main config file
            config_key (str): which loop_config key this object is handling.

        Raises:
            NotImplementedError: This is just a template
        """
        # please default to these naming conventions:

        if isinstance(main_config, Path):
            main_config = read_config(main_config, perform_validation=False)
        self.main_config = main_config
        self.config_key = config_key
        self.internal_config = self.create_internal_config(main_config, config_key)
        self.working_dir = Path(main_config["main_config"]["output_dir"]) / config_key

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
        extract the necessary informations from the main config and store them.

        Returns:
            dict: a dict of the sub config.
        """
        internal_config = main_config["loop_config"][config_key]
        return internal_config

    def create_slurm_scripts(self, slurm_config=None) -> str | Path:
        """Create the slurm script that is used to submit this calculation run to the server.
        This should use the slurm class provided in this module.
        """
        raise NotImplementedError

    def prepare_jobs(self, input_files) -> dict:
        """prepare the job files for submission.

        Args:
            input_files (list): list of input files.

        Returns:
            dict: a dict of the sub config.
        """
        raise NotImplementedError

    def run_job(self, key) -> None:
        """Interface to send the job to the server.

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError

    @classmethod
    def check_job_status(single_experiment) -> bool:
        """provide some method to verify if a single calculation was succesful.
        This should be handled indepentendly from the existence of this class object.

        """
        raise NotImplementedError
