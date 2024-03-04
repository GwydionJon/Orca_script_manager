from pathlib import Path


class CrestModule:
    """use config to setup a crest run.
    generate crest config as well as necessary slurm scripts.
    """

    def __init__(self, main_config: dict, config_key: str) -> None:
        super(CrestModule, self).__init__(main_config, config_key)
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
