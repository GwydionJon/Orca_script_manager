"""
This module provides functionality for working with ORCA files and preparing jobs for the ORCA module.

The module contains the following classes:
- OrcaModule: A class for setting up ORCA files and preparing jobs for the ORCA module.
"""

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
    0.65  # 65% of the available ram is used for orca this is subject to change
)


class OrcaModule(TemplateModule):
    """
    A class representing an Orca module.

    This class provides methods to set up Orca files from a main configuration,
    prepare jobs for the Orca module, and create slurm scripts for each configuration.

    Attributes:
        main_config (dict): The main configuration dictionary containing all the setup information.
        config_key (str): The key corresponding to the specific Orca setup in the main configuration.
    """

    def __init__(
        self,
        main_config: dict,
        config_key: str,
    ):
        """
        Initializes an OrcaModule object.

        This method sets up the orca files from the main config.
        Since different orca setups can be defined in the config,
        we need to pass the corresponding keyword (e.g., optimization or single_point).

        Args:
            main_config (dict): The main configuration dictionary containing all the setup information.
            config_key (str): The key corresponding to the specific orca setup in the main configuration.

        Raises:
            NotImplementedError: If a required method or feature is not implemented in a subclass.
        """
        super(OrcaModule, self).__init__(main_config, config_key)
        self.log.info(f"Creating orca object from key: {config_key}")

        # Set the orca version in the internal configuration
        self.internal_config["options"]["orca_version"] = self.main_config[
            "main_config"
        ]["orca_version"]

    def prepare_jobs(self, input_dirs, **kwargs) -> dict:
        """
        Prepares the jobs for the Orca module.

        This method reads XYZ files from the input directories,
        creates ORCA input files and slurm scripts,
        and returns a dictionary mapping directory stems to directory paths.

        Args:
            input_dirs (list): A list of directories to read the XYZ files from.
            kwargs: Arbitrary keyword arguments.

        Returns:
            dict: A dictionary mapping directory stems to directory paths.
        """
        input_files = []

        # Get the charge list and multiplicity list from the keyword arguments
        charge_list = kwargs.get("charge_list", [])
        multiplicity_list = kwargs.get("multiplicity_list", [])

        # Read the XYZ files from the input directories
        for input_dir in input_dirs:
            input_files.extend(list(input_dir.glob("*xyz")))

        # Read the XYZ files and create a dictionary of their information
        xyz_dict = self.read_xyzs(input_files, charge_list, multiplicity_list)

        # Create ORCA input files and prepare the slurm script
        orca_file_dict = self.create_orca_input_files(xyz_dict)
        orca_slurm_config = self.prepare_slurm_script(orca_file_dict)

        # Write the ORCA scripts and create the slurm scripts
        self.write_orca_scripts(orca_file_dict)
        self.create_slurm_scripts(orca_slurm_config)

        # Create a dictionary mapping directory stems to directory paths
        input_dir_dict = {input_dir.stem: input_dir for input_dir in input_dirs}
        return input_dir_dict

    def prepare_slurm_script(self, orca_file_dict, override_settings=None) -> dict:
        """
        Prepares a dictionary with the necessary variables to fill for a SLURM script.

        Variables to fill:

            - __jobname (str): Job name.
            - __ntasks (int): Number of tasks.
            - __memcore (int): Memory per core.
            - __walltime (str): Wall time.
            - __scratchsize (int): Scratch size.
            - __input_dir (str): Full path to the original input directory.
            - __output_dir (str): Full path to the original output directory.
            - __input_file (str): Relative path to the input file (this gets copied).
            - __output_file (str): Saves the ORCA output (full path to the original directory).
            - __marked_files (str): File paths in the format "/home/usr/dir/{file1,file2,file3,file4}".

        Args:
            orca_file_dict (dict): Dictionary with ORCA file information.
            override_settings (dict, optional): Dictionary with settings to override.

            Example: {"n_cores_per_calculation": 8, "ram_per_core": 8000, "walltime": "24:00:00"}

        Returns:
            dict: Dictionary with the variables to fill for the SLURM script.
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
        """
        Creates slurm scripts for each configuration in the slurm_config dictionary.

        This function reads a slurm template file,
        replaces placeholders in the template with values from the slurm_config dictionary,
        and writes the resulting slurm script to a new file in the working directory.

        Args:
            slurm_config (dict, optional): A dictionary containing slurm configurations.
            Each key is a filename stem and each value is a dictionary of placeholders and their replacements.

        Returns:
            dict: A dictionary mapping filename stems to the paths of the created slurm scripts.
        """

        # Initialize a dictionary to hold the paths of the created slurm scripts
        slurm_path_dict = {}

        # Read the slurm template file
        slurm_template_path = self.working_dir / "orca_template.sbatch"
        with open(slurm_template_path, "r", encoding="utf-8") as f:
            slurm_template = f.readlines()
        slurm_template = "".join(slurm_template)

        # Iterate over the slurm configurations
        for key, value in slurm_config.items():
            slurm_dict = value
            slurm_script = copy.copy(slurm_template)

            # Replace placeholders in the slurm template with values from the slurm configuration
            for replace_key, input_value in slurm_dict.items():
                slurm_script = slurm_script.replace(replace_key, str(input_value))

            # Create a new directory for the slurm script
            (self.working_dir / "input" / key).mkdir(parents=True, exist_ok=True)

            # Write the slurm script to a new file
            slurm_path_dict[key] = self.working_dir / "input" / key / f"{key}.sbatch"
            with open(slurm_path_dict[key], "w", encoding="utf-8") as f:
                f.write(slurm_script)

        # Return the dictionary of slurm script paths
        return slurm_path_dict

    def write_orca_scripts(self, orca_file_dict):
        """
        Writes ORCA input files for each entry in the orca_file_dict dictionary.

        This function creates a new directory for each ORCA input file, writes the input data to the file,
        and stores the path of the created file in a dictionary.

        Args:
            orca_file_dict (dict): A dictionary containing ORCA input data.
            Each key is a filename stem and each value is a list of lines to write to the file.

        Returns:
            dict: A dictionary mapping filename stems to the paths of the created ORCA input files.
        """

        # Initialize a dictionary to hold the paths of the created ORCA input files
        orca_path_dict = {}

        # Define the directory to write the ORCA input files to
        input_dir = self.working_dir / "input"

        # Iterate over the ORCA input data
        for key, value in orca_file_dict.items():
            # Create a new directory for the ORCA input file
            (input_dir / key).mkdir(parents=True, exist_ok=True)

            # Write the ORCA input data to a new file
            orca_path_dict[key] = input_dir / key / (key + ".inp")
            with open(orca_path_dict[key], "w", encoding="utf-8") as f:
                for item in value:
                    f.write("%s\n" % item)

        # Return the dictionary of ORCA input file paths
        return orca_path_dict

    def read_xyzs(self, input_files, charge_list, multiplicity_list):
        """
        Reads XYZ files and returns a dictionary with the file information.

        This function reads each XYZ file in the input_files list, extracts the coordinates,
        and stores them in a dictionary along with the charge and multiplicity.
        The dictionary is keyed by the stem of the XYZ file path.
        Each XYZ file is then moved to a new directory in the working directory.

        Args:
            input_files (list): A list of paths to the XYZ files.
            charge_list (list): A list of charges corresponding to the XYZ files.
            multiplicity_list (list): A list of multiplicities corresponding to the XYZ files.

        Returns:
            dict: A dictionary containing the coordinates, charge, and multiplicity for each XYZ file,
            keyed by the stem of the XYZ file path.
        """

        xyz_dict = {}

        # Iterate over the XYZ files, charges, and multiplicities
        for xyz_path, charge, multiplicity in zip(
            input_files, charge_list, multiplicity_list
        ):
            # Open the XYZ file and read the coordinates
            with open(xyz_path, "r", encoding="utf-8") as f:
                coords = f.readlines()[2:]

            # Remove trailing spaces and line breaks from the coordinates
            coords = [coord.strip() for coord in coords]

            # Store the coordinates, charge, and multiplicity in the dictionary
            xyz_dict[xyz_path.stem] = {
                "coords": coords,
                "charge": charge,
                "mul": multiplicity,
            }

            # Create a new directory in the working directory for the XYZ file
            (self.working_dir / "input" / xyz_path.stem).mkdir(
                parents=True, exist_ok=True
            )

            # Move the XYZ file to the new directory
            shutil.move(
                xyz_path,
                self.working_dir / "input" / xyz_path.stem / f"{xyz_path.stem}.xyz",
            )

        # Return the dictionary
        return xyz_dict

    def create_orca_input_files(self, xyz_dict):
        """
        Creates ORCA input files based on the provided XYZ dictionary and internal configuration.

        The internal configuration should include the following options:

        - method: The computational method to use.
        - basisset: The basis set to use.
        - additional_settings: Any additional settings for the calculation.
        - ram_per_core: The amount of RAM to allocate per core.
        - n_cores_per_calculation: The number of cores to use for the calculation.
        - args: Any additional arguments for the calculation.

        Args:
            xyz_dict (dict): A dictionary containing XYZ coordinates for the molecules.

        Example for additional arguments in the internal configuration:
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
        """
        Submits a job to the server using the SLURM workload manager.

        This function checks if the necessary SLURM and ORCA input files exist in the job's input directory.
        If they do, it submits the job using the `sbatch` command. If the `sbatch` command is not found,
        it raises a ValueError. If the necessary input files are not found, it raises a FileNotFoundError.

        Args:
            job (Job): The job object to be submitted. The job object should have a `current_dirs` attribute
                       that is a dictionary with a key "input" that maps to the directory containing the job's
                       input files. The name of the job is assumed to be the stem of this directory.

        Raises:
            ValueError: If the `sbatch` command is not found in the system's PATH.
            FileNotFoundError: If the necessary SLURM or ORCA input files are not found in the job's input directory.

        Returns:
            subprocess.CompletedProcess: The process object that was created by the subprocess.run command.
                                         This object can be used to check if the job was submitted successfully.
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
        """
        Restarts a list of jobs that failed due to a walltime error.

        This function iterates over the provided list of jobs, resetting each job and collecting the results.
        If the job failed due to a walltime error, it is skipped. Otherwise, the function collects the results
        of the job, creates a new XYZ input file based on the last coordinates of the job, and appends the job
        to a list of reset jobs. After all jobs have been processed, the function creates new ORCA input files
        and SLURM scripts for the reset jobs, and returns a tuple containing the list of reset jobs and a list
        of jobs that were not reset.

        Args:
            job_list (list): A list of Job objects to be restarted.
            key (str): The key to use when collecting the results of each job.

        Returns:
            tuple: A tuple containing two lists. The first list contains the Job objects that were reset. The
                second list contains the Job objects that were not reset.
        """

        # Initialize dictionaries and lists
        new_xyz_dict = {}
        reset_jobs_list = []

        # Log the number of jobs being restarted
        self.log.info(f"Restarting {len(job_list)} jobs")

        # Iterate over the list of jobs
        for job in job_list:

            # Reset the job and check the result
            reset_result = job.reset_key(self.config_key)
            if reset_result == "walltime_error":
                # If the job failed due to a walltime error, skip it
                continue

            # Collect the results of the job
            result_dict = OrcaModule.collect_results(job, key, "walltime_error")
            new_key = list(result_dict.keys())[0]

            # Get the last coordinates of the job
            last_xyz_coords = list(result_dict[new_key]["coords"].values())[-1]

            # Create a new XYZ input file based on the last coordinates
            new_xyz_input = [
                f"{atom['symbol']} {atom['x']} {atom['y']} {atom['z']}"
                for atom in last_xyz_coords
            ]
            new_xyz_dict[new_key] = {
                "coords": new_xyz_input,
                "charge": result_dict[new_key]["charge"],
                "mul": result_dict[new_key]["mult"],
            }

            # Remove the old files
            for file in job.current_dirs["input"].glob("*"):
                file.unlink()

            # Add the job to the list of reset jobs
            reset_jobs_list.append(job)

        # Override the walltime setting
        override_slurm_settings = {
            "walltime": self.main_config["main_config"]["max_run_time"]
        }

        # Create new ORCA input files and SLURM scripts for the reset jobs
        new_orca_file_dict = self.create_orca_input_files(new_xyz_dict)
        new_slurm_config = self.prepare_slurm_script(
            new_orca_file_dict, override_slurm_settings
        )

        # Write the new ORCA scripts and create the new SLURM scripts
        self.write_orca_scripts(new_orca_file_dict)
        self.create_slurm_scripts(new_slurm_config)

        # Get a list of jobs that were not reset
        non_reset_jobs = [job for job in job_list if job not in reset_jobs_list]

        # Return the list of reset jobs and the list of jobs that were not reset
        return reset_jobs_list, non_reset_jobs

    @classmethod
    def collect_results(cls, job, key, results_dir="finished") -> dict:
        """
        Uses the cclib library to extract the results from the ORCA output file.

        This function checks if the job's status for the given key is
        "finished" and if the results directory is "finished".
        If both conditions are met, it parses the output file and extracts the results.
        The results are then returned as a dictionary.
        If the conditions are not met, the function returns None.

        Args:
            job (Job): The current job object to collect results from.
            key (str): The key of the job to collect results from.
            results_dir (str, optional): The directory where the results are stored. Defaults to "finished".

        Returns:
            dict: A dictionary containing the results extracted from the ORCA output file.
            If the job's status for the given key
            is not "finished" or the results directory is not "finished", returns None.
        """

        # Check if the job's status for the given key is "finished" and if the results directory is "finished"
        if job.status_per_key[key] != "finished" and results_dir == "finished":
            # If not, return None
            return None

        # Parse the output file
        parse_output_file(job.current_dirs[results_dir])

        # Extract the results from the output file
        result_dict, _ = extract_infos_from_results(job.current_dirs[results_dir])

        # Return the results as a dictionary
        return result_dict

    @classmethod
    def check_job_status(cls, job: Job) -> str:
        """
        Checks the status of a job by examining the ORCA output file and the SLURM file.

        This function checks for various types of errors in the ORCA output file and the SLURM file.
        It returns a string indicating the status of the job: "success", "missing_ram_error", "walltime_error",
        "missing_files_error", or "unknown_error".

        Args:
            job (Job): The job object to check the status of.

        Returns:
            str: A string indicating the status of the job.
        """

        # Define a function to check for a SLURM walltime error in a text
        def check_slurm_walltime_error(input_text):
            pattern = re.compile(
                r"slurmstepd: error: \*\*\* JOB [0-9]+ ON [A-Za-z0-9]+ "
                + r"CANCELLED AT [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                + r"(\.[0-9]{1,3})? DUE TO TIME LIMIT \*\*\*",
                re.IGNORECASE,
            )
            return pattern.search(input_text)

        # Define a function to check for an ORCA memory error in a text
        def check_orca_memory_error(input_text):
            pattern = re.compile(
                r"Error  \(ORCA_SCF\): Not enough memory available!", re.IGNORECASE
            )
            return pattern.search(input_text)

        # Define a function to check for a normal ORCA termination in a text
        def check_orca_normal_termination(input_text):
            pattern = re.compile(r"ORCA TERMINATED NORMALLY")
            return pattern.search(input_text)

        # Get the output directory of the job
        job_out_dir = job.current_dirs["output"]

        # Get the ORCA output file
        orca_out_file = job_out_dir / (job_out_dir.stem + ".out")

        # Try to get the SLURM file
        try:
            slurm_file = list(job_out_dir.glob("slurm*"))[0]
        except IndexError:
            # If the SLURM file is not found, raise an exception
            raise Exception(f"Can't find slurm file in {job_out_dir} for job {job}")

        # Initialize the output string to "unknown_error"
        output_string = "unknown_error"

        # If the ORCA output file exists, check for errors in it
        if orca_out_file.exists():
            try:
                with open(orca_out_file, encoding="utf-8") as f:
                    file_contents = f.read()
            except UnicodeDecodeError:
                file_contents = _handle_encoding_error(orca_out_file)

            # Check for a normal ORCA termination
            if check_orca_normal_termination(file_contents):
                output_string = "success"
            # Check for an ORCA memory error
            if check_orca_memory_error(file_contents):
                output_string = "missing_ram_error"

        # If the SLURM file exists, check for a walltime error in it
        if slurm_file.exists():
            try:
                with open(slurm_file, encoding="utf-8") as f:
                    file_contents = f.read()
            except UnicodeDecodeError:
                file_contents = _handle_encoding_error(slurm_file)

            # Check for a SLURM walltime error
            if check_slurm_walltime_error(file_contents):
                output_string = "walltime_error"

        # If either the ORCA output file or the SLURM file does not exist,
        # set the output string to "missing_files_error"
        if not orca_out_file.exists() or not slurm_file.exists():
            output_string = "missing_files_error"

        # Return the output string
        return output_string


def _handle_encoding_error(filename):
    """
    Handles a UnicodeDecodeError when reading a file.

    This function reads a file as bytes and tries to decode it as UTF-8.
    If a UnicodeDecodeError occurs,
    it prints a message indicating the error and the last characters before the error occurred.
    It then reopens the file with error handling to replace the misbehaving character with a
    '?' and returns the file contents.


    Note that this function was designed for a specific problem
     manifesting in some test cases and should technically never be actually needed.

    Args:
        filename (str): The name of the file to read.

    Returns:
        str: The contents of the file, with misbehaving characters replaced by '?'.
    """

    # Read the file as bytes to find the misbehaving character
    with open(filename, "rb") as f:
        byte_data = f.read()

    try:
        # Try to decode the byte data as UTF-8
        byte_data.decode("utf-8")
        return
    except UnicodeDecodeError as e:
        # If a UnicodeDecodeError occurs, get the position of the error
        error_position = e.start

    # Decode the byte data up to the error position
    partial_decoded_data = byte_data[:error_position].decode("utf-8", errors="ignore")

    # Print a message indicating the error and the last characters before the error occurred
    print(
        f"An encoding error occured in {filename}. Unreadable symbol will be replaced by '?'"
    )
    print("Here are the last characters before the error occured:")
    print(partial_decoded_data[-500:])

    # Reopen the file with error handling to replace the misbehaving character with a '?'
    with open(filename, encoding="utf-8", errors="replace") as f:
        file_contents = f.read()

    # Return the file contents
    return file_contents
