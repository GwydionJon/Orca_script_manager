# this module is onlz intendet to be used as a template class and provides necessary function
# for another module to be properly useful in the scope of this program.
from pathlib import Path


class ModuleTemplate:

    def __init__(self, main_config, config_key) -> None:
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
        self.internal_config = self.create_internal_config(main_config, config_key)
        self.slurm_location = self.create_slurm_script()

    def create_internal_config(self, main_config, config_key) -> dict:
        """
        extract the necessary informations from the main config and store them.

        Returns:
            dict: a dict of the sub config.
        """
        raise NotImplementedError

    def create_slurm_script(self) -> str | Path:
        """Create the slurm script that is used to submit this calculation run to the server.
        This should use the slurm class provided in this module.
        """
        raise NotImplementedError

    def run_job(self) -> None:
        """Interface to send the job to the server.

        Raises:
            NotImplementedError: _description_
        """

    @classmethod
    def check_result_integrity(single_experiment) -> bool:
        """provide some method to verify if a single calculation was succesful.
        This should be handled indepentendly from the existence of this class object.

        """
        raise NotImplementedError
