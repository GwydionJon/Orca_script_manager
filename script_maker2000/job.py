import shutil
import subprocess


class Job:
    """This class will save all necessary information for a job.
    This inculdes current and past results, output and input files, and the main settings.
    """

    def __init__(
        self,
        input_id,
        all_keys,
        working_dir,
        charge,
        multiplicity,
        input_file_types=[".xyz"],
    ):
        """_summary_

        Args:
            input_file (str|Path): Location of the original input file.
            all_keys (list[str]): A list of all the calculation steps that will be performed by this job.
        """
        # public attributes
        self.mol_id = input_id
        self.unique_job_id = "__".join(all_keys) + "___" + input_id
        self.current_step = 0
        self.current_step_id = "START___" + input_id
        self.all_keys = all_keys

        # private attributes
        self.input_file_types = input_file_types
        self.charge = charge
        self.multiplicity = multiplicity

        self.current_key = "not_assigned"
        self._current_status = (
            "not_assigned"  # not_assigned,found, submitted, finished, failed
        )
        self.current_dirs = {
            "input": None,
            "output": None,
            "finished": None,
            "failed": None,
        }
        self.final_dir = None
        self.failed_reason = None

        # for each config_key this will save the location of the job_dir
        self.input_dir_per_key = {}
        self.output_dir_per_key = {}
        self.failed_per_key = {}
        self.finished_per_key = {}
        self.slurm_id_per_key = {}
        self.status_per_key = {}
        # this will be used to keep track of the jobs that are finished
        self.finished_keys = []

        self._init_all_dicts(working_dir, all_keys)

        # prepare final_output dirs
        self.raw_success_dir = (
            working_dir / "finished" / "raw_results" / self.unique_job_id
        )
        self.raw_failed_dir = working_dir / "failed" / self.unique_job_id

    def __repr__(self):
        return (
            "JOB: "
            + self.unique_job_id
            + " current_key: "
            + self.current_key
            + " current status: "
            + self.current_status
        )

    def _init_all_dicts(
        self,
        working_dir,
        all_keys,
    ):
        """_summary_

        Args:
            input_file (str|Path): Location of the original input file.
            all_keys (list[str]): A list of all the calculation steps that will be performed by this job.
        """

        for i, key in enumerate(all_keys):

            id_for_step = "__".join(all_keys[: i + 1]) + "___" + self.mol_id
            self.input_dir_per_key[key] = working_dir / key / "input" / id_for_step
            self.output_dir_per_key[key] = working_dir / key / "output" / id_for_step
            self.finished_per_key[key] = working_dir / key / "finished" / id_for_step
            self.failed_per_key[key] = working_dir / key / "failed" / id_for_step

    @property
    def current_status(self):
        return self._current_status

    @current_status.setter
    def current_status(self, value):
        self._current_status = value
        self.status_per_key[self.current_key] = value

    def _check_slurm_completed(self, key):
        process = subprocess.run(
            [
                shutil.which("sacct"),
                "-j",
                f"{self.slurm_id_per_key[key]}",
                "-o",
                "state",
            ],
            shell=False,
            check=False,
            capture_output=True,  # Python >= 3.7 only
            text=True,  # Python >= 3.7 only
            # shell = False is important on justus
        )
        process_out = process.stdout
        process_out = " ".join(process_out.split())

        if self.current_status == "submitted":
            if "COMPLETED" in process_out:
                self.current_status = "returned"
                return True
            else:
                return False

    def check_status_for_key(self, key):
        """Check the status of the job for the given key.

        Possible outputs are:
        - not_assigned
        - not_found
        - already_finished
        - found
        - submitted
        - returned
        - failed
        - finished
        Args:
            key (str): config key
        """

        if key not in self.all_keys:
            return "not_assigned"

        # if job previously failed, it will not be re-submitted
        if self.current_status == "failed":
            return "failed"

        if key != self.current_key and key not in self.finished_keys:
            return "not_found"

        if key != self.current_key and key in self.finished_keys:
            return "already_finished"

        if key in self.status_per_key:

            if self.status_per_key[key] == "submitted":
                print("checking slurm", self._check_slurm_completed(key))
                if self._check_slurm_completed(key):
                    return "returned"
                else:
                    return "submitted"

            return self.status_per_key[key]

        else:

            return "not_found"

    def start_new_key(self, key, step):
        """This sets all current attributes when the job is found by a new key.
            Will be called by the batch manager when copying the job to the new key.
        Args:
            key (str): config key
        """

        self.current_key = key
        self.current_step = step
        self.current_step_id = (
            "__".join(self.all_keys[: step + 1]) + "___" + self.mol_id
        )

        self.current_status = "found"
        self.status_per_key[key] = "found"

        self.current_dirs = {
            "input": self.input_dir_per_key[key],
            "output": self.output_dir_per_key[key],
            "finished": self.finished_per_key[key],
            "missing_ram_error": self.failed_per_key[key].parents[0]
            / "missing_ram_error"
            / self.failed_per_key[key].name,
            "walltime_error": self.failed_per_key[key].parents[0]
            / "walltime_error"
            / self.failed_per_key[key].name,
            "unknown_error": self.failed_per_key[key].parents[0]
            / "unknown_error"
            / self.failed_per_key[key].name,
        }

    def manage_return(self, return_str):
        """
        Currently the possible return_str are:
        - success
        - missing_ram_error
        - walltime_error
        - unknown_error

        Args:
            return_str (str): error string from the work module
        """

        if return_str == "success":
            self.current_status = "finished"
            if not self.current_dirs["finished"].exists():
                shutil.copytree(
                    self.current_dirs["output"], self.current_dirs["finished"]
                )

        else:
            self.current_status = "failed"
            self.failed_reason = return_str

            if not self.current_dirs[self.failed_reason].exists():
                shutil.copytree(
                    self.current_dirs["output"], self.current_dirs[self.failed_reason]
                )

        # # clean up input and output by archiving
        # for dir in [self.current_dirs["input"], self.current_dirs["output"]]:
        #     shutil.make_archive(dir.parents[0] / ("archive_" + dir.stem), "gztar", dir)
        #     shutil.rmtree(dir)

    def advance_to_next_key(self):
        """Advance to the next key and update the current status and directories.

        This method is used to advance to the next key in the job, update the current status and
        directories accordingly.

        Args:
            current_key (str): The current key.
            next_key (str): The next key to advance to.
            input_file_types (list, optional): A list of input file types to consider. Defaults to [".xyz"].
        """

        current_key = self.current_key
        self.status_per_key[current_key] = self.current_status
        self.finished_keys.append(current_key)
        if current_key != self.all_keys[-1]:
            next_key = self.all_keys[self.all_keys.index(current_key) + 1]

            if self.current_status == "finished":

                self.start_new_key(next_key, self.current_step + 1)

                for input_file_type in self.input_file_types:

                    for input_file in self.finished_per_key[current_key].glob(
                        f"*{input_file_type}"
                    ):

                        new_input_dir = self.current_dirs["input"]
                        new_input_dir.mkdir(parents=True, exist_ok=True)
                        new_file_name = self.current_step_id + input_file.suffix
                        new_file = new_input_dir / new_file_name

                        if not new_file.exists():
                            shutil.copy(input_file, new_file)
                        else:
                            return "file_exists"
                return "success"

            elif self.current_status == "failed":

                self.wrap_up_failed()

                return self.failed_reason

            else:
                return "not_finished"

        else:
            if self.current_status == "finished":

                self.wrap_up()
                return "finalized"
            else:
                return self.current_status

    def wrap_up_failed(self):
        """
        Performs the necessary actions when a job fails.

        This method copies the current directory associated with the failed reason to a final directory,
        sets the status of the current key to "failed", and sets the status of all remaining keys to "failed".

        Returns:
            str: The reason for the job failure.
        """
        if self.final_dir is not None:
            self.current_dirs[self.failed_reason]
            self.final_dir = self.raw_failed_dir
            # self.final_dir.mkdir(parents=True, exist_ok=True)
            if not (self.final_dir / self.unique_job_id).exists():
                shutil.copytree(
                    self.current_dirs[self.failed_reason],
                    self.final_dir / self.unique_job_id,
                )

            self.status_per_key[self.current_key] = "failed"
            # set failed for all remaining keys
            for key in self.all_keys[self.all_keys.index(self.current_key) + 1 :]:
                self.status_per_key[key] = "failed"

        return self.failed_reason

    def wrap_up(self):
        """
        Performs the necessary actions when a job is finished.

        This method copies all current finished files into the final success directory.

        Returns:
        str: The status of the job.
        """

        current_dir = self.current_dirs["finished"]
        print(current_dir)
        self.final_dir = self.raw_success_dir
        self.current_status = "finalized"

        # Copy all finished files to the final success directory
        shutil.copytree(current_dir, self.final_dir / self.unique_job_id)

    def prepare_initial_job(self, key, step, input_file):
        """Prepare the initial job for execution.

        This method prepares the initial job for execution by copying the input file to the correct input directory.

        Args:
            key (str): The key for the job.
            step (int): The step number for the job.
            input_file (Path): The input file with the correct name.

        Returns:
            None
        """
        self.start_new_key(key, step)

        # Copy the input files to the correct input directory
        self.current_dirs["input"].mkdir(parents=True, exist_ok=True)

        new_file = self.current_dirs["input"] / (
            self.current_step_id + input_file.suffix
        )
        if not new_file.exists():
            # Only create the file if it does not exist
            # When using parallel jobs, the file of a primary stage might be needed for multiple secondary stages
            # but we don't want to make the calculation multiple times
            shutil.copy(input_file, new_file)
