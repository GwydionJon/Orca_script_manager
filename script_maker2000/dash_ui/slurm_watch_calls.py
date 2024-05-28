from collections import defaultdict

# import json
from pathlib import Path

# import dash_bootstrap_components as dbc
# from dash import html
import pandas as pd

sacct_dict = Path(__file__).parent / "sacct_options.json"


def get_sacct_output(
    n_clicks, start_date, end_date, time_range, format_entries, remote_connection
):
    sacct_command = "sacct -p"

    start_time = f"{time_range[0]}:00"
    end_time = f"{time_range[1]}:00"

    if start_date:
        start_time = f"{start_date}T" + start_time
    if end_date:
        if time_range[1] == 24:
            time_range[1] = "00"
            end_date = end_date[:-1] + str(int(end_date[-1]) + 1)
        end_time = f"{end_date}T" + end_time

    sacct_command += f" -S {start_time} -E {end_time}"

    if format_entries:
        sacct_command += f" --format={','.join(format_entries)}"
    slurm_output = remote_connection.run(sacct_command, hide=True).stdout

    split_rows = slurm_output.split("\n")
    row_dict = defaultdict(dict)
    for i, row in enumerate(split_rows):
        if i == 0:
            column_names = row.split("|")
        else:
            row_values = row.split("|")
            if len(row_values) == 1:
                continue
            row_dict[row_values[0]] = {
                column_names[i]: row_values[i] for i in range(1, len(column_names))
            }

    df = pd.DataFrame(row_dict).T
    df.reset_index(inplace=True)
    columns = [{"name": i, "id": i} for i in df.columns[:-1]]

    return df.to_dict("records"), columns
