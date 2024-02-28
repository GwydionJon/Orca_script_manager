class Slurm_Script:

    def __init__(self, main_config: dict, specific_config: dict):

        raise NotImplementedError()

        self.file_location = None
        self.input_template = None
        self.slurm_config = None

    def ceate_slurm_config(self, config: dict):
        """Filter the main config for relevant slurm settings and create a new config file for just the slurm operations

        Args:
            main_config (dict): _description_

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError()

        # write config to corresponding directory

    def submit_slurm_script(self):
        """
        Main function to submit a new script to the cli.
        """

        raise NotImplementedError()
