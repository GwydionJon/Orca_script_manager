def create_working_dir_structure(main_config: dict):
    """
       This function generates the data structure for further calculations.
        a main folder with a folder for crest, optimzation, sp and result sub folders
        as well as the corresponding config files.
        In each of these subfolders will be an input, and an output folder.
        These always contain pairs of molecule files and slurm files.

    Args:
        main_config (dict):The main working folder can be extracted from this config dict

    Raises:
        NotImplementedError: _description_
    """
    raise NotImplementedError()

    # check if folder is empty, if not raise warning.


def move_files(start, end):
    """simple wrapper for moving files and handling certain logic requiremens before doing so. TODO

    Args:
        start (str): input file
        end (str): output file

    Raises:
        NotImplementedError: _description_
    """
    raise NotImplementedError()
