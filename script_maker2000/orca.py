from pathlib import Path
import logging
import copy
from datetime import datetime
import subprocess


from script_maker2000.template import TemplateModule

script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


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
        script_maker_log.info(f"Creating orca object from key: {config_key}")
        super(OrcaModule, self).__init__(main_config, config_key)
        self.internal_config["options"]["orca_version"] = self.main_config[
            "main_config"
        ]["orca_version"]

        # get xyz data
        xyz_dict = self.read_xyzs()
        orca_file_dict = self.create_orca_input_files(xyz_dict)

        self.orca_slurm_config = self.prepare_slurm_script(config_key, orca_file_dict)

        self.write_orca_scripts(orca_file_dict)
        self.slurm_path_dict = self.create_slurm_scripts()

    def prepare_slurm_script(self, config_key, orca_file_dict) -> str | Path:
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
                "__jobname": f"{config_key}_{key}",
                "__VERSION": options["orca_version"],
                "__ntasks": options["n_cores_per_calculation"],
                "__memcore": options["ram_per_core"],
                "__walltime": options["walltime"],
                "__scratchsize": options["disk_storage"],
                "__input_dir": working_dir / "input",
                "__output_dir": working_dir / "output" / f"{key}",
                "__input_file": f"{key}.inp",
                "__output_file": working_dir / "output" / f"{key}" / f"{key}.out",
                "__marked_files": f"{key}.inp",
                "__timestemp": date_str,
            }

        return slurm_dict

    def create_slurm_scripts(self) -> str | Path:
        """Create the slurm script that is used to submit this calculation run to the server.
        This should use the slurm class provided in this module.

        """
        # read slurm template and merge lines in one string

        slurm_path_dict = {}

        slurm_template_path = self.working_dir / "orca_template.sbatch"
        with open(slurm_template_path, "r") as f:
            slurm_template = f.readlines()
        slurm_template = "".join(slurm_template)

        for key, value in self.orca_slurm_config.items():
            slurm_dict = value
            slurm_script = copy.copy(slurm_template)

            for replace_key, input_value in slurm_dict.items():
                print(replace_key, input_value)
                slurm_script = slurm_script.replace(replace_key, str(input_value))

            slurm_path_dict[key] = self.working_dir / "input" / f"{key}.sbatch"

            with open(self.working_dir / "input" / f"{key}.sbatch", "w") as f:
                f.write(slurm_script)
            return slurm_path_dict

    def write_orca_scripts(self, orca_file_dict):
        input_dir = self.working_dir / "input"

        for key, value in orca_file_dict.items():
            with open(input_dir / (key + ".inp"), "w") as f:
                for item in value:
                    f.write("%s\n" % item)

    def read_xyzs(self):

        xyz_dir = self.working_dir / "input"
        if not isinstance(xyz_dir, Path):
            xyz_dir = Path(xyz_dir)

        xyz_files = xyz_dir.glob("*.xyz")

        xyz_dict = {}

        for xyz_path in xyz_files:
            with open(xyz_path, "r") as f:
                charge_mul_coords = f.readlines()[1:]
                # remove trailing spaces and line breaks
            charge_mul = charge_mul_coords[0]

            coords = [coord.strip() for coord in charge_mul_coords[1:]]
            charge = int(charge_mul.split("charge:")[1].split(",")[0])
            mul = int(charge_mul.split("multiplicity:")[1])
            xyz_dict[xyz_path.stem] = {
                "coords": coords,
                "charge": charge,
                "mul": mul,
            }

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
        maxcore = options["ram_per_core"]
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
            coords = value["coords"]
            charge = value["charge"]
            mul = value["mul"]

            orca_file_dict[key] = copy.deepcopy(setup_lines)
            orca_file_dict[key].append(f"* xyz {charge} {mul}")
            orca_file_dict[key] += coords
            orca_file_dict[key].append("*")

        return orca_file_dict

    def run_job(self, key) -> None:
        """Interface to send the job to the server.

        Returns:
            subprocess.CompletedProcess: the process object that was created by the subprocess.run command.
            can be used to check for succesful submission.
        """

        import shutil

        slurm_job = self.slurm_path_dict[key]
        script_maker_log.info(f"Submitting orca job: {key}")
        script_maker_log.info(f"Slurm script: {slurm_job}")

        if shutil.which("sbatch"):
            process = subprocess.run(
                [shutil.which("sbatch"), str(slurm_job)], shell=True
            )
        else:
            raise FileNotFoundError(
                "sbatch not found in path. Please make sure that slurm is installed on your system."
            )

        return process

    @classmethod
    def check_result_integrity(single_experiment) -> bool:
        """provide some method to verify if a single calculation was succesful.
        This should be handled indepentendly from the existence of this class object.

        """
        raise NotImplementedError
