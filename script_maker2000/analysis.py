import json
from collections import defaultdict

from pathlib import Path
import cclib
import numpy as np
import datetime


single_value_entries = [
    "charge",
    "enthalpy",
    "entropy",
    "freeenergy",
    "mult",
    "natom",
    "nmo",
    "nbasis",
    "optdone",
    "preassure",
    "temperature",
    "zpve",
]

multi_value_entries = ["scfenergies", "final_sp_energy"]

dict_entries = [
    "energy_corrections",
    "metadata",
]

special_entries = ["vibfreqs"]


def extract_infos_from_results(raw_output_files: list) -> dict:
    """
    Extracts the information from the output files and adds it to the job_dict.
    """

    if isinstance(raw_output_files, str):
        raw_output_files = Path(raw_output_files)

        out_files = list(raw_output_files.glob("**/*_calc_result.json"))

    elif isinstance(raw_output_files, list):
        out_files = []
        for output_dir in raw_output_files:
            if not Path(output_dir).is_dir():
                raise ValueError(f"Directory {output_dir} does not exist.")
            out_files.extend(list(Path(output_dir).glob("**/*_calc_result.json")))

    elif isinstance(raw_output_files, Path):
        out_files = list(raw_output_files.glob("**/*_calc_result.json"))

    elif raw_output_files is None:
        return {}

    else:
        raise ValueError(
            f"raw_output_files must be a string, a list of strings or a Path object but is {type(raw_output_files)}."
        )

    result_dict = defaultdict(dict)
    corrections_list = []

    for out_file in out_files:
        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        filename = out_file.name.split("_calc_result.json")[0]

        result_dict[filename]["dirname"] = str(Path(out_file).parents[0])
        result_dict[filename]["filename"] = filename
        for key, value in data.items():

            if key in single_value_entries:
                if key == "optdone":
                    result_dict[filename][key] = bool(value)
                    continue
                result_dict[filename][key] = value
            elif key in multi_value_entries:
                result_dict[filename][key] = value[-1]
            elif key in dict_entries:
                if key == "energy_corrections":
                    total_corr = 0
                    for corr_key, corr_value in value.items():
                        result_dict[filename][corr_key + "_correction"] = corr_value[-1]
                        if corr_key + "_correction" not in corrections_list:
                            corrections_list.append(corr_key + "_correction")
                        total_corr += corr_value[-1]
                    result_dict[filename]["total_correction"] = total_corr
                elif key == "metadata":
                    result_dict[filename]["metadata_package"] = (
                        value["package"] + " v" + value["package_version"]
                    )
                    result_dict[filename]["metadata_basisset"] = value["basis_set"]
                    result_dict[filename]["metadata_functional"] = value["keywords"][0]
                    result_dict[filename]["metadata_method"] = " ".join(
                        set(value["methods"])
                    ).strip()
                    result_dict[filename]["metadata_keywords"] = " ".join(
                        value["keywords"][1:]
                    )
            elif key in special_entries:
                result_dict[filename]["imaginary_freq"] = all(
                    freq < 0 for freq in value
                )
    return result_dict, corrections_list


def parse_output_file(output_dir):

    def _convert_np_to_list(item):
        if isinstance(item, dict):
            return {k: _convert_np_to_list(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [_convert_np_to_list(element) for element in item]
        elif isinstance(item, np.ndarray):
            return item.tolist()
        elif isinstance(item, datetime.timedelta):
            return str(item)
        else:
            return item

    output_dir = Path(output_dir)
    output_file = output_dir / (output_dir.stem + ".out")
    json_file = output_dir / (output_dir.stem + "_calc_result.json")
    try:
        cclib_results = cclib.io.ccread(str(output_file))
    except Exception as e:
        print(f"Error: {e}")  # cclib_results = cclib_results.parse()
        raise e
    cclib_attr = cclib_results.getattributes()

    result_dict = _convert_np_to_list(cclib_attr)

    # save the results in a json file
    with open(
        json_file,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(result_dict, f)
