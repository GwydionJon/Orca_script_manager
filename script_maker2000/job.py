import shutil
from pathlib import Path
import pint


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

        if isinstance(working_dir, str):
            working_dir = Path(working_dir)

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
        self.final_dirs = {}
        self._failed_reason = None

        self.efficiency_data = {}

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

        # self.tqdm = None

        # prepare final_output dirs
        self.raw_success_dir = working_dir / "finished" / "raw_results" / self.mol_id
        self.raw_failed_dir = self.raw_success_dir / "failed"

        self._overlapping_jobs = []

    def __repr__(self):
        rep_str = (
            "JOB: "
            + self.unique_job_id
            + " current_key: "
            + self.current_key
            + " current status: "
            + self.current_status
        )
        if self.current_status == "failed":
            rep_str += " failed reason: " + self.failed_reason
        return rep_str

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
            self.input_dir_per_key[key] = (
                working_dir / "working" / key / "input" / id_for_step
            )
            self.output_dir_per_key[key] = (
                working_dir / "working" / key / "output" / id_for_step
            )
            self.finished_per_key[key] = (
                working_dir / "working" / key / "finished" / id_for_step
            )
            self.failed_per_key[key] = (
                working_dir / "working" / key / "failed" / id_for_step
            )

    @property
    def current_status(self):
        return self._current_status

    @current_status.setter
    def current_status(self, value):
        self._current_status = value
        self.status_per_key[self.current_key] = value

        # set status for all overlapping jobs
        if value in ["submitted", "finished", "failed"]:

            if value == "submitted":
                value = "submitted_overlapping_job"
            for overlapping_job in self.overlapping_jobs:
                if (
                    overlapping_job.current_key == self.current_key
                    and overlapping_job.current_status != value
                ):
                    overlapping_job._current_status = value  # noqa
                    overlapping_job.status_per_key[self.current_key] = value
                    overlapping_job.slurm_id_per_key[self.current_key] = (
                        self.slurm_id_per_key[self.current_key]
                    )

    @property
    def failed_reason(self):
        return self._failed_reason

    @failed_reason.setter
    def failed_reason(self, value):
        self._failed_reason = value
        for overlapping_job in self.overlapping_jobs:
            if overlapping_job.failed_reason is None:
                overlapping_job._failed_reason = value

    @property
    def overlapping_jobs(self):
        return self._overlapping_jobs

    @overlapping_jobs.setter
    def overlapping_jobs(self, value):
        self._overlapping_jobs = value

    def check_status_for_key(self, key, ignore_overlapping_jobs=True):
        """Check the status of the job for the given key.

        Possible outputs are:
        - not_assigned
        - not_found
        - already_finished
        - found
        - submitted
        - submitted_overlapping_job
        - returned
        - failed
        - finished
        - missing_output
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
            if (
                self.status_per_key[key] == "submitted_overlapping_job"
                and ignore_overlapping_jobs
            ):
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

        checked_status = self.check_status_for_key(key)
        if checked_status != "submitted":

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
            "missing_output": self.failed_per_key[key].parents[0]
            / "missing_output"
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
                shutil.move(self.current_dirs["output"], self.current_dirs["finished"])
        else:
            self.current_status = "failed"
            self.failed_reason = return_str

            if not self.current_dirs[self.failed_reason].exists():

                shutil.move(
                    self.current_dirs["output"], self.current_dirs[self.failed_reason]
                )

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

        if current_key != self.all_keys[-1]:
            next_key = self.all_keys[self.all_keys.index(current_key) + 1]

            if self.current_status == "finished":

                old_step_id = self.current_step_id
                old_finished_dir = self.current_dirs["finished"]
                self.start_new_key(next_key, self.current_step + 1)
                if current_key not in self.finished_keys:
                    self.finished_keys.append(current_key)

                    for input_file_type in self.input_file_types:
                        input_file = old_finished_dir / (old_step_id + input_file_type)

                        new_input_dir = self.current_dirs["input"]
                        new_input_dir.mkdir(parents=True, exist_ok=True)
                        new_file_name = self.current_step_id + input_file_type
                        new_file = new_input_dir / new_file_name

                        if not new_file.exists():
                            shutil.copy(input_file, new_file)
                        else:
                            return "file_exists"
                    return "success"

            elif self.current_status == "failed":
                if current_key not in self.finished_keys:
                    self.finished_keys.append(current_key)

                self.wrap_up_combined()

                return self.failed_reason

            else:
                return "not_finished"

        else:
            # if the current key is the last key, the job is finished
            if self.current_status in ["finished", "failed"]:
                self.finished_keys.append(current_key)
                # self.tqdm.update()

                return_str = self.wrap_up_combined()

            else:
                return_str = "not_finished"

            return return_str

    def _clean_up(self):
        """Clean up the input and output directories.

        This method is used to clean up the input and output directories by archiving them and then removing them.
        """
        dir_list = list(self.output_dir_per_key.values()) + list(
            self.input_dir_per_key.values()
        )
        for dir in dir_list:
            if dir.exists():
                shutil.make_archive(
                    dir.parents[0] / ("archive_" + dir.stem), "gztar", dir
                )
                shutil.rmtree(dir)

    def wrap_up_combined(self):

        wrap_up_return_str = "finalized"

        final_dir = self.raw_success_dir

        for key in self.finished_keys:  # pylint: disable=C0206

            if key in self.final_dirs.keys():
                continue

            key_id = (
                "__".join(self.all_keys[: self.all_keys.index(key) + 1])
                + "___"
                + self.mol_id
            )

            if self.status_per_key[key] == "finished":
                src_dir = self.finished_per_key[key]
                target_dir = final_dir / key_id

            elif self.status_per_key[key] == "failed":
                src_dir = (
                    self.failed_per_key[key].parents[0] / self.failed_reason / key_id
                )
                target_dir = final_dir / "failed" / self.failed_reason / key_id

                wrap_up_return_str = self.failed_reason

                if self.failed_reason == "missing_output":
                    src_dir.mkdir(parents=True, exist_ok=True)
                    missing_file = src_dir / "missing_output.txt"
                    with open(missing_file, "w", encoding="utf-8") as f:
                        f.write(
                            f"No output files found in the output directory for job: {self}."
                        )
            else:
                continue
            if (target_dir).exists():
                continue

            # check if overlapping jobs have already started the next key. if not skip
            for overlapping_job in self.overlapping_jobs:
                continuing = False
                if overlapping_job.current_key == key:
                    if overlapping_job.current_status == "found":
                        continuing = True
                if continuing:
                    continue

            shutil.move(src_dir, target_dir)

            self.final_dirs[key] = target_dir

        self._clean_up()
        return wrap_up_return_str

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

    def export_as_dict(self):

        export_dict = {}
        export_dict["mol_id"] = self.mol_id
        export_dict["unique_job_id"] = self.unique_job_id
        export_dict["current_step"] = self.current_step
        export_dict["current_step_id"] = self.current_step_id
        export_dict["all_keys"] = self.all_keys
        export_dict["input_file_types"] = self.input_file_types
        export_dict["charge"] = int(self.charge)
        export_dict["multiplicity"] = int(self.multiplicity)
        export_dict["current_key"] = self.current_key
        export_dict["_current_status"] = self._current_status
        export_dict["finished_keys"] = self.finished_keys
        export_dict["final_dirs"] = {
            key: str(value) for key, value in self.final_dirs.items()
        }
        export_dict["failed_reason"] = self.failed_reason

        export_dict["slurm_id_per_key"] = {
            str(key): str(value) for key, value in self.slurm_id_per_key.items()
        }
        export_dict["status_per_key"] = {
            str(key): str(value) for key, value in self.status_per_key.items()
        }

        export_dict["efficiency_data"] = self.export_efficiency_data()
        return export_dict

    @classmethod
    def import_from_dict(cls, input_dict, working_dir):
        new_job = cls(
            input_dict["mol_id"],
            input_dict["all_keys"],
            working_dir,
            input_dict["charge"],
            input_dict["multiplicity"],
            input_dict["input_file_types"],
        )
        new_job.current_step = input_dict["current_step"]
        new_job.current_step_id = input_dict["current_step_id"]
        new_job.current_key = input_dict["current_key"]
        new_job._current_status = input_dict["_current_status"]

        new_job.current_dirs = {
            "input": new_job.input_dir_per_key[new_job.current_key],
            "output": new_job.output_dir_per_key[new_job.current_key],
            "finished": new_job.finished_per_key[new_job.current_key],
            "missing_ram_error": new_job.failed_per_key[new_job.current_key].parents[0]
            / "missing_ram_error"
            / new_job.failed_per_key[new_job.current_key].name,
            "walltime_error": new_job.failed_per_key[new_job.current_key].parents[0]
            / "walltime_error"
            / new_job.failed_per_key[new_job.current_key].name,
            "unknown_error": new_job.failed_per_key[new_job.current_key].parents[0]
            / "unknown_error"
            / new_job.failed_per_key[new_job.current_key].name,
        }

        new_job.final_dirs = {
            key: Path(value) for key, value in input_dict["final_dirs"].items()
        }
        new_job.failed_reason = input_dict["failed_reason"]

        new_job.slurm_id_per_key = input_dict["slurm_id_per_key"]
        new_job.status_per_key = input_dict["status_per_key"]
        new_job.finished_keys = input_dict["finished_keys"]

        new_job.efficiency_data = {
            int(key): value for key, value in input_dict["efficiency_data"].items()
        }

        return new_job

    def export_efficiency_data(self):

        str_dict = {}
        for slurm_key, data in self.efficiency_data.items():
            str_dict[slurm_key] = {}
            for key, value in data.items():
                if isinstance(value, pint.Quantity):
                    str_dict[slurm_key][key] = str(value.to_compact())
                else:
                    str_dict[slurm_key][key] = value
        return str_dict
