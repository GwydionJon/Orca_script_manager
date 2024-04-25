import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State

# import dash_treeview_antd as dta


from script_maker2000.dash_ui.config_maker_ui import create_new_intput

from script_maker2000.dash_ui.results_window_calls import (
    update_results_config_,
    get_job_progress_dict_,
    get_jobs_overview,
    download_results_,
    hide_download_column_when_local,
    update_results_folder_select,
)

default_style = {"margin": "10px", "width": "100%"}


def create_results_layout():

    top_row_layout = create_top_row_layout()

    layout = dbc.Col(
        [
            top_row_layout,
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3("Results"),
                            html.Div(id="results_div"),
                        ],
                        width=3,
                    ),
                ],
                style=default_style,
            ),
        ],
        style=default_style,
    )
    return layout


def create_top_row_layout():
    layout = dbc.Row(
        [
            dbc.Col(
                [
                    html.H4("Choose Results Folder", style=default_style),
                    dbc.RadioItems(
                        id="lokal_remote_radio",
                        options=[
                            {"label": "Local", "value": "local"},
                            {"label": "Remote", "value": "remote"},
                        ],
                        value="remote",
                        inline=True,
                        style=default_style,
                    ),
                    dbc.Button(
                        "Refresh",
                        id="refresh_results_config",
                        color="primary",
                        style=default_style,
                    ),
                    dcc.Store(id="results_config_store"),
                    dcc.Store(id="job_progress_dict_store"),
                    dcc.Loading(
                        [
                            dbc.Select(
                                id="results_config_select",
                                options=[],
                                style=default_style,
                            ),
                            dbc.Select(
                                id="results_folder_select",
                                options=[],
                                style=default_style,
                            ),
                        ]
                    ),
                    create_new_intput(
                        "Custom Output Directoy (takes priority!)",
                        "",
                        id_="custom_output_dir_input",
                        placeholder="Enter a custom path when your desired path is not shown.",
                        debounce=True,
                    ),
                ],
                width=3,
            ),
            dbc.Col(
                [
                    html.H4("Progress overview", style=default_style),
                    dbc.Textarea(
                        id="job_progress_textarea",
                        style={"margin": "10px", "width": "100%", "height": "300px"},
                        placeholder="Job progress will be displayed here.",
                        readonly=True,
                    ),
                ],
                width=3,
            ),
            dbc.Col(
                [
                    html.H4("Download Results", style=default_style),
                    create_new_intput(
                        "Local Target Directory",
                        "",
                        id_="local_target_dir_input",
                        placeholder="Choose a folder (relative or absolute path). Empty means the cwd.",
                    ),
                    create_new_intput(
                        "Exlude pattern from zip (seperate by comma)",
                        ".gbw,",
                        id_="exclude_pattern_input",
                        placeholder="Exlude pattern from zip (seperate by comma)",
                    ),
                    dbc.Button(
                        id="download_results_button",
                        style=default_style,
                        children="Download Results",
                    ),
                    dcc.Loading(
                        dbc.Input(
                            id="download_results_output",
                            style=default_style,
                            placeholder="Download status will be displayed here.",
                            readonly=True,
                        )
                    ),
                ],
                id="download_results_col",
                width=3,
            ),
        ],
        style=default_style,
    )
    return layout


def add_callbacks_results(app, remote_connection):

    def update_results_config(n_clicks, remote_local_switch, results_config_value):

        options, results_config_value, config_dict = update_results_config_(
            n_clicks, remote_local_switch, results_config_value, remote_connection
        )
        return options, results_config_value, config_dict

    def get_job_progress_dict(calculation_dir, custom_calc_dir, remote_local_switch):

        job_progress_dict = get_job_progress_dict_(
            calculation_dir, custom_calc_dir, remote_local_switch, remote_connection
        )

        return job_progress_dict

    def download_results(
        n_clicks, results_folder_value, target_dir, exclude_pattern_value
    ):
        """_summary_

        Args:
            n_clicks (_type_): trigger for the fucntion (unused.)
            results_folder_value (str): The remote directory to download.
            target_dir (str): The local directory to download to.
            exclude_pattern_value (str): The pattern to exclude from the zip file. Egs. ".gbw, .log" or even "backup"

        Raises:
            e: _description_

        Returns:
            str: Result message.
        """
        result_str = download_results_(
            n_clicks,
            results_folder_value,
            target_dir,
            exclude_pattern_value,
            remote_connection,
        )
        return result_str

    app.callback(
        Output("results_config_select", "options"),
        Output("results_config_select", "value"),
        Output("results_config_store", "data"),
        Input("refresh_results_config", "n_clicks"),
        Input("lokal_remote_radio", "value"),
        State("results_config_select", "value"),
        prevent_initial_call=False,
    )(update_results_config)

    app.callback(
        Output("results_folder_select", "options"),
        Output("results_folder_select", "value"),
        Output("download_results_output", "value", allow_duplicate=True),
        Input("results_config_select", "value"),
        State("results_config_store", "data"),
        State("results_folder_select", "value"),
        prevent_initial_call=True,
    )(update_results_folder_select)

    app.callback(
        Output("job_progress_dict_store", "data"),
        Input("results_folder_select", "value"),
        Input("custom_output_dir_input", "value"),
        State("lokal_remote_radio", "value"),
        prevent_initial_call=True,
    )(get_job_progress_dict)

    app.callback(
        Output("job_progress_textarea", "value"),
        Input("job_progress_dict_store", "data"),
        prevent_initial_call=True,
    )(get_jobs_overview)

    app.callback(
        Output("download_results_output", "value", allow_duplicate=True),
        Input("download_results_button", "n_clicks"),
        State("results_folder_select", "value"),
        State("local_target_dir_input", "value"),
        State("exclude_pattern_input", "value"),
        prevent_initial_call=True,
    )(download_results)

    app.callback(
        Output("download_results_col", "style"),
        Input("lokal_remote_radio", "value"),
        prevent_initial_call=True,
    )(hide_download_column_when_local)

    return app
