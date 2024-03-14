from pathlib import Path
import copy
from datetime import datetime
import subprocess
import shutil
import re
from script_maker2000.template import TemplateModule


class OrcaModule(TemplateModule):

    # Handles an entire batch of orca jobs at once.
    #   This includes config setup, creation of Orca_Scripts and
    # corresponding slurm scripts as well as handeling the submission logic.

    def __init__(
        self,
        main_config: dict,
        config_key: str,
    ) -> None:
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

    def prepare_slurm_script(self, orca_file_dict) -> str | Path:
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
        """
        options = self.internal_config["options"]
        slurm_dict = {}
        # Get current date
        current_date = datetime.now()

        # Format date as a string with abbreviated year, hours, minutes, and seconds
        date_str = current_date.strftime("%dd_%mm_%yy-%Hh_%Mm_%Ss")
        working_dir = self.working_dir.resolve()

        for key in orca_file_dict.keys():
            slurm_dict[key] = {
                "__jobname": f"{self.config_key}_{key}",
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

    def create_slurm_scripts(self, slurm_config=None) -> str | Path:
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

        orca_ram_scaling = (
            0.75  # 75% of the available ram is used for orca this is subject to change
        )

        options = self.internal_config["options"]
        # extract setup from config
        method = options["method"]
        basisset = options["basisset"]
        add_setting = options["additional_settings"]
        maxcore = options["ram_per_core"] * orca_ram_scaling
        nprocs = options["n_cores_per_calculation"]
        args = options["args"]

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

    def run_job(self, job_dir) -> None:
        """Interface to send the job to the server.

        Returns:
            subprocess.CompletedProcess: the process object that was created by the subprocess.run command.
            can be used to check for succesful submission.
        """
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
                f"Can't find slurm file: {slurm_file} or orca file: {orca_file}."
                + " Please check your file name or provide the necessary files."
            )
        return process

    @classmethod
    def check_job_status(cls, job_out_dir: str | Path) -> int:
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

        if isinstance(job_out_dir, str):
            job_out_dir = Path(job_out_dir)

        # check for walltime error
        if list(job_out_dir.glob("walltime_error.txt")):
            return "walltime_error"

        # get orca output file
        orca_out_file = job_out_dir / (job_out_dir.stem + ".out")
        slurm_file = list(job_out_dir.glob("slurm*"))[0]

        # check for orca errors only if xyz file exists

        if orca_out_file.exists():
            with open(orca_out_file) as f:
                file_contents = f.read()

                if check_orca_normal_termination(file_contents):
                    return "success"
                if check_orca_memory_error(file_contents):
                    return "missing_ram_error"
        if slurm_file.exists():
            with open(slurm_file) as f:
                file_contents = f.read()
                if check_slurm_walltime_error(file_contents):
                    return "walltime_error"

        return "unknown_error"
