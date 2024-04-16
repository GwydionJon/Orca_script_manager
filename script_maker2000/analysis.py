import numpy as np
from molmass import Formula

import json

from collections import defaultdict
import pandas as pd
import pint
import pint_pandas

import plotly.express as px


ureg = pint.UnitRegistry(cache_folder=":auto:")
pint_pandas.PintType.ureg = ureg


def load_job_backup(file_path: str) -> dict:

    with open(file_path, "r") as file:
        data = json.load(file)
    return data


def _quantify_with_units(df, column):
    # Split values and units
    split_df = df[column].str.split(" ", expand=True)
    values = split_df[0].astype(float)
    units = split_df[1]

    # create new list of ureg quantities

    new_list = []
    for value, unit in zip(values, units):
        new_list.append(ureg.Quantity(value, unit))

    preferred_units = [ureg.seconds, ureg.joules, ureg.gigabyte]
    ureg.default_preferred_units = preferred_units
    base_unit_quantities = [q.to_preferred() for q in new_list]

    for i, q in enumerate(base_unit_quantities):
        if "byte" not in str(q.units):
            break
        else:
            base_unit_quantities[i] = q.to(ureg.gigabyte)

    df[column] = [q.magnitude for q in base_unit_quantities]
    df[column] = df[column].astype(f"pint[{str(base_unit_quantities[0].units)}]")


def extract_efficency_dataframe(
    job_dict, filter_list, columns_with_units=None
) -> pd.DataFrame:
    """
    Extracts the efficiency data from the dataframe and returns a new dataframe with the efficiency data.
    """

    # list of filter keys

    if columns_with_units is None:
        columns_with_units = [
            "CPUTimeRAW",
            "ElapsedRaw",
            "TimelimitRaw",
            "ConsumedEnergyRaw",
            "MaxDiskRead",
            "MaxDiskWrite",
            "MaxVMSize",
            "ReqMem",
        ]

    new_dict = defaultdict(lambda: defaultdict(dict))

    for job in job_dict.values():
        for filter_key in filter_list:
            for efficiency_key, efficiency_val in job["efficiency_data"].items():
                if filter_key in efficiency_key:
                    # exclude failed jobs
                    if job["failed_reason"] is not None:
                        continue

                    # new_dict[filter_key][efficiency_key][job["mol_id"]] =
                    # {"efficiency_data":efficiency_val, "unique_job_id":job["unique_job_id"]}
                    # new_dict[(filter_key,efficiency_key,job["mol_id"])]["unique_job_id"] = job["unique_job_id"]
                    for eff_key, eff_value in efficiency_val.items():
                        if eff_key in ["ExitCode", "JobName", "JobID"]:
                            continue
                        new_dict[(filter_key, efficiency_key, job["mol_id"])][
                            eff_key
                        ] = eff_value

    df = pd.DataFrame(new_dict).T.sort_index()

    df.index.set_names(["Method", "Method_options", "Mol_Id"], inplace=True)
    df["Molecule"] = df.index.get_level_values("Mol_Id")

    columns_with_units = [
        "CPUTimeRAW",
        "ElapsedRaw",
        "TimelimitRaw",
        "ConsumedEnergyRaw",
        "MaxDiskRead",
        "MaxDiskWrite",
        "MaxVMSize",
        "ReqMem",
    ]

    for column in columns_with_units:
        _quantify_with_units(df, column)
    df = df.pint.dequantify()
    df["mol_weight"] = df["Molecule"].apply(lambda x: Formula(x.values[0]).mass, axis=1)

    return df


def filter_dataframe(df, filter_method=None, filter_mol=None):

    if filter_method:
        if "freq" in filter_method:
            mask = df.index.get_level_values("Method") == filter_method
        else:
            # leave out any method that contains freq
            mask = ~df.index.get_level_values("Method_options").str.contains("freq")
            mask &= df.index.get_level_values("Method") == filter_method

    else:
        mask = True

    if filter_mol:
        mask &= df.index.get_level_values("Mol_Id") == filter_mol

    return df[mask]


def plot_efficiency(df, x_axis_label, y_axis_label, molecules=None):

    if molecules is not None:
        df = df[df["Molecule"].isin(molecules)]

    # extract the x and y axis as numpy arrays first

    x_axis = df[x_axis_label].to_numpy().flatten()
    y_axis = df[y_axis_label].to_numpy().flatten()

    fig = px.scatter(
        x=x_axis,
        y=y_axis,
        color=df["Molecule"].to_numpy().flatten(),
        labels={"x": x_axis_label, "y": y_axis_label},
        title=f"Time plot for {df.index.get_level_values('Method')[0]}",
    )
    fig.show()


def estimate_total_run_time(
    df_filtered, n_jobs, available_cpus, average_molecules=False
):
    run_dict = defaultdict(dict)

    for mol in df_filtered.index.get_level_values("Mol_Id").unique():
        df_filtered_mol = filter_dataframe(df_filtered, filter_mol=mol)

        n_cpus = df_filtered_mol["NCPUS"].values.flatten()
        time_per_run = df_filtered_mol["ElapsedRaw"].values.flatten()

        parallel_jobs = np.floor(available_cpus / n_cpus)

        n_runs = np.ceil(n_jobs / parallel_jobs)

        total_time = n_runs * time_per_run

        for n_cpu, total_time_ in zip(n_cpus, total_time):
            run_dict[n_cpu][mol] = total_time_
    if average_molecules:

        return {
            n_cpu: np.mean(list(run_dict[n_cpu].values())) for n_cpu in run_dict.keys()
        }
    else:
        return run_dict


def estimate_runtime_all_methods(
    df, filter_methods=None, n_jobs=100, available_cpus=48
):
    run_dict = defaultdict(dict)

    if filter_methods is None:
        filter_methods = df.index.get_level_values("Method").unique()

    for method in filter_methods:
        df_filtered_method = filter_dataframe(df, filter_method=method)
        run_dict[method] = estimate_total_run_time(
            df_filtered_method, n_jobs, available_cpus, average_molecules=True
        )

    df_ = pd.DataFrame(run_dict).T
    df_.index.rename("Method")
    conversion_to_hours = 3600
    df_ = df_.apply(
        lambda x: x / conversion_to_hours if np.issubdtype(x.dtype, np.number) else x
    )
    return df_


def scan_optimal_cpu_count(
    df, filter_methods=None, min_runs=1, max_runs=120, step_size=5, available_cpus=48
):
    result_dict = defaultdict(dict)

    if filter_methods is None:
        filter_methods = df.index.get_level_values("Method").unique()

    for n in range(min_runs, max_runs, step_size):
        result_n = estimate_runtime_all_methods(
            df, filter_methods=filter_methods, n_jobs=n, available_cpus=available_cpus
        )
        for method in filter_methods:
            result_dict[method][n] = result_n.loc[method].idxmin()

    return pd.DataFrame(result_dict)
