from script_maker2000.analysis import (
    load_job_backup,
    extract_efficency_dataframe,
    filter_dataframe,
)
from pathlib import Path


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
