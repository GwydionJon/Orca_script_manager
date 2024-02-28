class Crest_Job:
    """use config to setup a crest run.
    generate crest config as well as necessary slurm scripts.
    """

    def __init__(self, main_config: dict) -> None:
        raise NotImplementedError

    def create_slurm_scripts(self):
        """_summary_

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError

    def run_crest_jobs(self):
        """Start the number of crest jobs defined in the config."""
        raise NotImplementedError
