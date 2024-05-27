from script_maker2000.cpu_benchmark_analysis import (
    load_job_backup,
    extract_efficency_dataframe,
    filter_dataframe,
)

from script_maker2000.analysis import (
    extract_infos_from_results,
    parse_output_file,
    basic_connectivity_check,
)
from pathlib import Path
import pytest


def test_extract_efficency_dataframe():

    file_path = (
        Path(__file__).parent / "test_data" / "analysis_job_backup" / "job_backup.json"
    )
    job_backup = load_job_backup(file_path)
    filter_list = ["PBEh_3c_opt", "r2SCAN3c", "PBEh3c_freq", "B3LYP_D4", "PBEh3c"]

    eff_df = extract_efficency_dataframe(job_backup, filter_list)
    assert eff_df.shape == (496, 11)
    assert set(eff_df.index.get_level_values(0).unique()) == set(filter_list)

    df_filtered = filter_dataframe(eff_df, "PBEh3c_freq")
    assert df_filtered.shape == (96, 11)


def test_parse_and_extract(analysis_tmp_dir):

    output_test_files = list(analysis_tmp_dir.glob("*.out"))

    for file in output_test_files:
        parse_output_file(file)

    assert len(list(analysis_tmp_dir.glob("*.json"))) == 4

    cc_file = list(analysis_tmp_dir.glob("dlpno_qz_calc_result.json"))[0]

    result_dict, _ = extract_infos_from_results(cc_file)
    result_dict = result_dict["dlpno_qz"]
    assert "metadata_package" in result_dict.keys()
    assert "ccenergies" in result_dict.keys()
    assert "T1 Diagnostic" in result_dict.keys()

    imag_freq_file = list(analysis_tmp_dir.glob("FREQ_Sb_5_M016973_calc_result.json"))[
        0
    ]
    result_dict, _ = extract_infos_from_results(imag_freq_file)
    result_dict = result_dict["FREQ_Sb_5_M016973"]
    assert "metadata_package" in result_dict.keys()
    assert "imaginary_freq" in result_dict.keys()
    assert "freeenergy" in result_dict.keys()
    assert "Dispersion_correction" in result_dict.keys()

    assert result_dict["imaginary_freq"] is True

    freq_file = list(
        analysis_tmp_dir.glob(
            "PBEh_3c_opt__PBEh3c_freq_2cores_sp___C3H9GeNOS_calc_result.json"
        )
    )[0]

    result_dict, _ = extract_infos_from_results(freq_file)
    result_dict = result_dict["PBEh_3c_opt__PBEh3c_freq_2cores_sp___C3H9GeNOS"]
    assert "metadata_package" in result_dict.keys()
    assert "Dispersion_correction" in result_dict.keys()

    assert result_dict["imaginary_freq"] is False


def test_basic_connectivity_check():
    # Test with valid dict input
    calc_results_dict = {
        "metadata": {"coords": [["H", 0.0, 0.0, 0.0], ["O", 0.0, 0.0, 1.0]]},
        "coords": {
            "0": [
                {"symbol": "H", "x": 0.0, "y": 0.0, "z": 0.0},
                {"symbol": "O", "x": 0.0, "y": 0.0, "z": 1.0},
            ]
        },
    }
    assert basic_connectivity_check(calc_results_dict) is True

    # Test with invalid input type
    calc_results_invalid = ["invalid", "input"]
    with pytest.raises(ValueError):
        basic_connectivity_check(calc_results_invalid)

    # Test with dict input where the structure has changed during the calculation
    calc_results_changed = {
        "metadata": {
            "coords": [
                ["H", 0.0, 0.0, 0.0],
                ["O", 0.0, 0.0, 1.0],
                ["H", 0.0, 0.0, 12.0],
            ]
        },
        "coords": {
            "0": [
                {"symbol": "H", "x": 0.0, "y": 0.0, "z": 0.0},
                {"symbol": "O", "x": 0.0, "y": 0.0, "z": 2.0},
                {"symbol": "H", "x": 0.0, "y": 0.0, "z": 1.0},
            ]
        },  # changed coords
    }
    assert basic_connectivity_check(calc_results_changed) is False
