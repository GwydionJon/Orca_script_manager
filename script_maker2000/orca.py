from pathlib import Path
import copy
import datetime
import subprocess
import shutil
import re
from typing import Union
from script_maker2000.template import TemplateModule
from script_maker2000.job import Job
from script_maker2000.analysis import extract_infos_from_results, parse_output_file


orca_ram_scaling = (
    0.65  # 75% of the available ram is used for orca this is subject to change
)


class OrcaModule(TemplateModule):

    # Handles an entire batch of orca jobs at once.
    #   This includes config setup, creation of Orca_Scripts and
    # corresponding slurm scripts as well as handeling the submission logic.

    def __init__(
        self,
        main_config: dict,
        config_key: str,
    ):
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
        self.log.info(f"Creating orca object from key: {config_key}")

        self.internal_config["options"]["orca_version"] = self.main_config[
            "main_config"
        ]["orca_version"]

    def prepare_jobs(self, input_dirs, **kwargs) -> dict:
        input_files = []

        charge_list = kwargs.get("charge_list", [])
        multiplicity_list = kwargs.get("multiplicity_list", [])

        for input_dir in input_dirs:
            input_files.extend(list(input_dir.glob("*xyz")))

        xyz_dict = self.read_xyzs(input_files, charge_list, multiplicity_list)

        orca_file_dict = self.create_orca_input_files(xyz_dict)
        orca_slurm_config = self.prepare_slurm_script(orca_file_dict)

        self.write_orca_scripts(orca_file_dict)
        self.create_slurm_scripts(orca_slurm_config)

        # get the input dir list
        input_dir_dict = {input_dir.stem: input_dir for input_dir in input_dirs}
        return input_dir_dict

    def prepare_slurm_script(self, orca_file_dict, override_settings=None) -> dict:
        """

        Variables to fill:
        __jobname : str
        __ntasks : int
        __memcore : int
        __walltime : str
        __scratchsize : int
        __input_dir : full path to original dir
        __output_dir : full path to original dir
        __input_file : rel path to input file (this gets copied)
        __output_file : saves the orca output (full path to original dir)
        __marked_files : str /home/usr/dir/{file1,file2,file3,file4}

        override_settings: dict
        example: {"n_cores_per_calculation": 8, "ram_per_core": 8000, "walltime": "24:00:00"}

        """
        options = self.internal_config["options"]

        if isinstance(override_settings, dict):
            for key, value in override_settings.items():
                options[key] = value

        elif override_settings is not None:
            raise TypeError(
                f"Override settings must be a dict but is {type(override_settings)}"
            )

        slurm_dict = {}
        # Get current date
        current_date = datetime.datetime.now()

        # Format date as a string with abbreviated year, hours, minutes, and seconds
        date_str = current_date.strftime("%dd_%mm_%yy-%Hh_%Mm_%Ss")
        working_dir = self.working_dir.resolve()

        for key in orca_file_dict.keys():
            slurm_dict[key] = {
                "__jobname": f"{key}",
                "__VERSION": options["orca_version"],
                "__ntasks": options["n_cores_per_calculation"],
                "__memcore": options["ram_per_core"],
                "__walltime": options["walltime"],
                "__scratchsize": options["disk_storage"],
                "__input_dir": working_dir / "input" / key,
                "__output_dir": working_dir / "output" / f"{key}",
                "__input_file": f"{key}.inp",
                "__output_file": working_dir / "output" / f"{key}" / f"{key}.out",
                "__marked_files": f"{key}.inp",
                "__timestemp": date_str,
            }
        return slurm_dict

    def create_slurm_scripts(self, slurm_config=None) -> Union[str, Path]:
        """Create the slurm script that is used to submit this calculation run to the server.
        This should use the slurm class provided in this module.

        """
        # read slurm template and merge lines in one string

        slurm_path_dict = {}
        slurm_template_path = self.working_dir / "orca_template.sbatch"
        with open(slurm_template_path, "r", encoding="utf-8") as f:
            slurm_template = f.readlines()
        slurm_template = "".join(slurm_template)

        for key, value in slurm_config.items():
            slurm_dict = value
            slurm_script = copy.copy(slurm_template)

            for replace_key, input_value in slurm_dict.items():
                slurm_script = slurm_script.replace(replace_key, str(input_value))

            (self.working_dir / "input" / key).mkdir(parents=True, exist_ok=True)
            slurm_path_dict[key] = self.working_dir / "input" / key / f"{key}.sbatch"

            with open(
                self.working_dir / "input" / key / f"{key}.sbatch",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(slurm_script)

        return slurm_path_dict

    def write_orca_scripts(self, orca_file_dict):
        input_dir = self.working_dir / "input"
        orca_path_dict = {}
        for key, value in orca_file_dict.items():

            (input_dir / key).mkdir(parents=True, exist_ok=True)
            orca_path_dict[key] = input_dir / key / (key + ".inp")
            with open(input_dir / key / (key + ".inp"), "w", encoding="utf-8") as f:
                for item in value:
                    f.write("%s\n" % item)
        return orca_path_dict

    def read_xyzs(self, input_files, charge_list, multiplicity_list):

        xyz_dict = {}

        for xyz_path, charge, multiplicity in zip(
            input_files, charge_list, multiplicity_list
        ):
            with open(xyz_path, "r", encoding="utf-8") as f:
                coords = f.readlines()[2:]
                # remove trailing spaces and line breaks

            coords = [coord.strip() for coord in coords]

            xyz_dict[xyz_path.stem] = {
                "coords": coords,
                "charge": charge,
                "mul": multiplicity,
            }
            (self.working_dir / "input" / xyz_path.stem).mkdir(
                parents=True, exist_ok=True
            )
            shutil.move(
                xyz_path,
                self.working_dir / "input" / xyz_path.stem / f"{xyz_path.stem}.xyz",
            )

        return xyz_dict

    def create_orca_input_files(self, xyz_dict):
        """
        config explanation:
        To use additional arguments provide them in the args section of the specific config.
        use the following dict style:
        key:value
        key: block keyword (https://sites.google.com/site/orcainputlibrary/general-input)
        value: provide a list of argument + value strings.

        example:
            {"scf": ["MAXITER 0"], "elprop": ["Polar 1","Solver C"] }

        """

        options = self.internal_config["options"]

        # extract setup from config
        method = options["method"]
        basisset = options["basisset"]
        add_setting = options["additional_settings"]
        maxcore = options["ram_per_core"] * orca_ram_scaling
        nprocs = options["n_cores_per_calculation"]
        args = options["args"]

        for argument in [method, basisset, add_setting]:
            if argument == "empty":
                argument = ""

        # start setting the pieces for the orca file

        setup_lines = []
        setup_lines.append(f"!{method} {basisset} {add_setting}")
        setup_lines.append(f"%maxcore {maxcore}")
        setup_lines.append(f"%pal nprocs = {nprocs}  end")
        for key, arg_list in args.items():
            setup_lines.append(f"%{key}")
            for arg in arg_list:
                setup_lines.append(f"{arg}")
            setup_lines.append("end")

        orca_file_dict = {}

        for key, value in xyz_dict.items():
            orca_file_dict[key] = copy.deepcopy(setup_lines)

            orca_file_dict[key].append("%output XYZFILE 1 end")

            coords = value["coords"]
            charge = value["charge"]
            mul = value["mul"]

            orca_file_dict[key].append(f"* xyz {charge} {mul}")
            orca_file_dict[key] += coords
            orca_file_dict[key].append("*")

        return orca_file_dict

    def run_job(self, job) -> None:
        """Interface to send the job to the server.

        Returns:
            subprocess.CompletedProcess: the process object that was created by the subprocess.run command.
            can be used to check for succesful submission.
        """

        job_dir = job.current_dirs["input"]
        key = job_dir.stem
        slurm_file = job_dir / (key + ".sbatch")
        orca_file = job_dir / (key + ".inp")
        self.log.debug(
            f"Submitting orca job: {key} with slurm file: {slurm_file} and orca file: {orca_file}"
        )

        if slurm_file.is_file() and orca_file.is_file():

            if shutil.which("sbatch"):
                process = subprocess.run(
                    [shutil.which("sbatch"), str(slurm_file)],
                    shell=False,
                    check=False,
                    capture_output=True,
                    text=True,
                    # shell = False is important on justus
                )
            else:
                raise ValueError(
                    "sbatch not found in path. Please make sure that slurm is installed on your system."
                )

        else:
            raise FileNotFoundError(
                f"Can't find slurm file: {slurm_file} or orca file: {orca_file} for job {job}."
                + " Please check your file name or provide the necessary files."
            )
        return process

    def restart_jobs(self, job_list, key):
        """Restart a list of jobs that failed due to a walltime error."""

        new_xyz_dict = {}
        reset_jobs_list = []

        self.log.info(f"Restarting {len(job_list)} jobs")

        for job in job_list:

            reset_result = job.reset_key(self.config_key)
            if reset_result == "walltime_error":
                continue

            result_dict = OrcaModule.collect_results(job, key, "walltime_error")
            new_key = list(result_dict.keys())[0]

            last_xyz_coords = list(result_dict[new_key]["coords"].values())[-1]

            new_xyz_input = [
                f"{atom['symbol']} {atom['x']} {atom['y']} {atom['z']}"
                for atom in last_xyz_coords
            ]
            new_xyz_dict[new_key] = {
                "coords": new_xyz_input,
                "charge": result_dict[new_key]["charge"],
                "mul": result_dict[new_key]["mult"],
            }

            # remove the old files
            for file in job.current_dirs["input"].glob("*"):
                file.unlink()

            reset_jobs_list.append(job)

        override_slurm_settings = {
            "walltime": self.main_config["main_config"]["max_run_time"]
        }
        new_orca_file_dict = self.create_orca_input_files(new_xyz_dict)
        new_slurm_config = self.prepare_slurm_script(
            new_orca_file_dict, override_slurm_settings
        )

        self.write_orca_scripts(new_orca_file_dict)
        self.create_slurm_scripts(new_slurm_config)

        non_reset_jobs = [job for job in job_list if job not in reset_jobs_list]

        return reset_jobs_list, non_reset_jobs

    @classmethod
    def collect_results(cls, job, key, results_dir="finished") -> dict:
        """Use the cclib library to extract the results from the orca output file.

        Args:
            job (Job): current job object to collect results from.
            key (str): the key of the job to collect results from.
            results_dir (str): the directory where the results are stored.
        Returns:
            dict: _description_
        """

        # prepare the cclib result dict for storage

        # get the output file
        if job.status_per_key[key] != "finished" and results_dir == "finished":
            return None

        # first parse the output file and get result json

        parse_output_file(job.current_dirs[results_dir])

        result_dict, _ = extract_infos_from_results(job.current_dirs[results_dir])

        return result_dict

    @classmethod
    def check_job_status(cls, job: Job) -> int:
        """provide some method to verify if a single calculation was succesful.
        This should be handled indepentendly from the existence of this class object.


        """

        def check_slurm_walltime_error(input_text):
            pattern = re.compile(
                r"slurmstepd: error: \*\*\* JOB [0-9]+ ON [A-Za-z0-9]+ "
                + r"CANCELLED AT [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                + r"(\.[0-9]{1,3})? DUE TO TIME LIMIT \*\*\*",
                re.IGNORECASE,
            )
            return pattern.search(input_text)

        def check_orca_memory_error(input_text):
            pattern = re.compile(
                r"Error  \(ORCA_SCF\): Not enough memory available!", re.IGNORECASE
            )
            return pattern.search(input_text)

        def check_orca_normal_termination(input_text):
            pattern = re.compile(r"ORCA TERMINATED NORMALLY")
            return pattern.search(input_text)

        job_out_dir = job.current_dirs["output"]

        # get orca output file
        orca_out_file = job_out_dir / (job_out_dir.stem + ".out")
        try:
            slurm_file = list(job_out_dir.glob("slurm*"))[0]
        except IndexError:
            raise Exception(f"Can't find slurm file in {job_out_dir} for job {job}")
        # check for orca errors only if xyz file exists

        output_string = "unknown_error"

        if orca_out_file.exists():
            try:
                with open(
                    orca_out_file,
                    encoding="utf-8",
                ) as f:
                    file_contents = f.read()
            except UnicodeDecodeError:
                file_contents = _handle_encoding_error(orca_out_file)

            if check_orca_normal_termination(file_contents):
                output_string = "success"
            if check_orca_memory_error(file_contents):
                output_string = "missing_ram_error"

        if slurm_file.exists():
            try:
                with open(
                    slurm_file,
                    encoding="utf-8",
                ) as f:
                    file_contents = f.read()
            except UnicodeDecodeError:
                file_contents = _handle_encoding_error(slurm_file)

            if check_slurm_walltime_error(file_contents):
                output_string = "walltime_error"

        if not orca_out_file.exists() or not slurm_file.exists():
            output_string = "missing_files_error"
        return output_string


def _handle_encoding_error(filename):

    # read file as bytes to find the misbehaving character
    with open(filename, "rb") as f:
        byte_data = f.read()

    try:
        byte_data.decode("utf-8")
    except UnicodeDecodeError as e:
        error_position = e.start

    # Decode up to the error position
    partial_decoded_data = byte_data[:error_position].decode("utf-8", errors="ignore")

    print(
        f"An encoding error occured in {filename}. Unreadable symbol will be replaced by '?'"
    )
    print("Here are the last characters before the error occured:")
    print(partial_decoded_data[-500:])

    # now open the file with the error handling
    with open(filename, encoding="utf-8", errors="replace") as f:
        file_contents = f.read()
    return file_contents
