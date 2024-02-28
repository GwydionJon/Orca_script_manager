class Orca_Script:
    """This class manages the creation of the orca setup scripts"""

    def __init__(self, main_config) -> None:
        """create orca sript"""
        raise NotImplementedError

    def save_script(self):
        """Save the script to disk."""
        raise NotImplementedError()


class Orca_Calculations:
    """
    Handles an entire batch of orca jobs at once.
    This includes config setup, creation of Orca_Scripts and
    corresponding slurm scripts as well as handeling the submission logic.
    """

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
        raise NotImplementedError()
        self.orca_config = None
        self.working_dir = None
        self.orca_input = None
        self.orca_output = None

    def create_orca_config(self, main_config: dict):

        raise NotImplementedError

    def create_orca_batch(self):
        """Take batch information from the orca config and prepare relevnt files.

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError()

    def run_orca_jobs(self):
        """Start the number of orca jobs defined in the config."""

        raise NotImplementedError()
