from script_maker2000.template import TemplateModule
from pathlib import Path


class Orca_Script:
    """This class manages the creation of the orca setup scripts"""

    def __init__(self, main_config) -> None:
        """create orca sript"""
        raise NotImplementedError

    def save_script(self):
        """Save the script to disk."""
        raise NotImplementedError()


class OrcaModule(TemplateModule):

    # Handles an entire batch of orca jobs at once.
    #   This includes config setup, creation of Orca_Scripts and
    # corresponding slurm scripts as well as handeling the submission logic.

    def __init__(self, main_config: dict, config_key: str) -> None:
        """Setup the orca files from the main config.
        Since different orca setups can be defined in the config
        we need to pass the corresponding kyword ( eg.: opimization or single_point)

        Args:
            main_config (dict): _description_
            config_key (str): _description_

        Raises:
            NotImplementedError: _description_
        """
        super(OrcaModule, self).__init__(main_config, config_key)
        self.slurm_location = None

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
