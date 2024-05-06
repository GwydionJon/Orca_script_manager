import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, dash_table

from dash_bio import Speck

import dash_treeview_antd as dta


from script_maker2000.dash_ui.config_maker_ui import create_new_intput

from script_maker2000.dash_ui.results_window_calls import (
    update_results_config_,
    get_job_progress_dict_,
    get_jobs_overview,
    download_results_,
    hide_download_column_when_local,
    update_results_folder_select,
    create_results_file_tree,
    update_table_values,
    download_table_data,
    update_detailed_screen_header,
    update_xyz_slider,
    update_xyz_data,
    update_energy_convergence_plot,
    update_simulated_ir_spectrum,
)

default_style = {"margin": "10px", "width": "100%"}


def create_results_layout():

    top_row_layout = create_top_row_layout()
    results_table_row = create_results_table_row()
    layout = dbc.Col(
        [
            top_row_layout,
            results_table_row,
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


def create_results_table():
    table_row = [
        dbc.Row([dcc.Store(id="complete_results_dict_store", data={})]),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Checklist(
                            id="results_table_columns_checklist",
                            options=[
                                {
                                    "label": "Molecular Informations",
                                    "value": "mol_info",
                                },
                                {
                                    "label": "Calculation Setup",
                                    "value": "calc_setup",
                                },
                                {"label": "Energies", "value": "energies"},
                                {
                                    "label": "Thermodynamics",
                                    "value": "thermo",
                                },
                            ],
                            value=[
                                "mol_info",
                                "calc_setup",
                                "energies",
                                "thermo",
                            ],
                            inline=True,
                        )
                    ]
                ),
                dbc.Col(
                    [
                        dbc.Row(html.P("Energy Unit:")),
                        dbc.Row(
                            [
                                dbc.Select(
                                    id="energy_unit_select",
                                    options=[
                                        {"label": "eV", "value": "eV"},
                                        {
                                            "label": "Hartree",
                                            "value": "hartree",
                                        },
                                        {
                                            "label": "kcal/mol",
                                            "value": "kcal/mol",
                                        },
                                        {
                                            "label": "kJ/mol",
                                            "value": "kJ/mol",
                                        },
                                    ],
                                    value="kJ/mol",
                                    style={"width": "50%"},
                                )
                            ]
                        ),
                    ]
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Button(
                    id="download_table_button",
                    style={"margin": "10px", "width": "30%"},
                    children="Download Table",
                )
            ]
        ),
        dbc.Row(
            [
                dcc.Loading(
                    dash_table.DataTable(
                        id="results_table",
                        columns=[],
                        merge_duplicate_headers=True,
                        filter_action="native",
                        filter_options={"placeholder_text": "Filter column..."},
                        sort_action="native",
                        sort_mode="multi",
                        row_selectable="single",
                        style_table={
                            "overflowX": "auto",
                            "overflowY": "auto",
                            "height": "500px",
                        },
                    ),
                )
            ]
        ),
    ]
    return table_row


def create_detailed_results_screen():
    layout = [
        dcc.Store(id="detailed_results_store", data={}),
        dbc.Fade(
            children=[
                dbc.Row(
                    html.H3(
                        "Detailed Results Screen for: ",
                        id="detailed_results_screen_header",
                        style=default_style,
                    ),
                ),
                dbc.Row(html.H4("Molecular Structure", style=default_style)),
                dbc.Row(
                    dcc.Loading(
                        Speck(
                            id="speck",
                            view={
                                "resolution": 400,
                                "ao": 0.1,
                                "outline": 1,
                                "atomScale": 0.25,
                                "relativeAtomScale": 0.33,
                                "bonds": True,
                            },
                            style={"width": "600px"},
                        )
                    ),
                    style=default_style,
                ),
                dbc.Row(
                    dbc.Fade(
                        dcc.Slider(
                            id="speck_slider",
                            min=0,
                            max=0,
                            value=0,
                            tooltip={
                                "placement": "bottom",
                                "always_visible": True,
                            },
                        ),
                        is_in=True,
                        id="speck_slider_fade",
                    ),
                    style={"width": "30%"},
                ),
                dbc.Row(
                    dbc.Fade(
                        [
                            html.H4("Energy Convergence Plot", style=default_style),
                            dcc.Graph(id="energy_convergence_plot"),
                        ],
                        is_in=False,
                        id="energy_convergence_plot_fade",
                    ),
                    style=default_style,
                ),
                dbc.Row(
                    dbc.Fade(
                        [
                            html.H4("Simulated IR Spectrum", style=default_style),
                            dcc.Graph(id="simulated_ir_spectrum_graph"),
                        ],
                        is_in=False,
                        id="simulated_ir_spectrum_graph_fade",
                    ),
                    style=default_style,
                ),
            ],
            id="detailed_results_screen_fade",
            is_in=False,
        ),
    ]

    return layout


def create_results_table_row():

    layout = dbc.Row(
        [
            html.H4("Results"),
            html.P(
                [
                    "Only local files are shown here. Select files or folders as you see fit.",
                    html.Br(),
                    "This programm will only show finished calculations for further analysis.",
                ]
            ),
            dbc.Col(
                [
                    dbc.Row(
                        [
                            create_new_intput(
                                "Filter files",
                                "",
                                "results_file_filter_input",
                                "seperate multiple filters by comma",
                                debounce=True,
                            ),
                            dcc.Loading(
                                dta.TreeView(
                                    id="results_treeview",
                                    multiple=False,
                                    checkable=True,
                                )
                            ),  # noqa
                        ]
                    ),
                ],
                width=3,
            ),
            dbc.Col(
                [
                    dbc.Row(create_results_table(), style=default_style),
                    dbc.Row(create_detailed_results_screen(), style=default_style),
                ],
                width=9,
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
        return (
            result_str,
            {},
        )  # Reset the complete_results_dict_store when downloading a new output.

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
        Output("complete_results_dict_store", "data", allow_duplicate=True),
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

    app.callback(
        Output("results_treeview", "data"),
        Input("results_file_filter_input", "value"),
        prevent_initial_call=False,
    )(create_results_file_tree)

    app.callback(
        Output("results_table", "data"),
        Output("results_table", "columns"),
        Output("complete_results_dict_store", "data", allow_duplicate=True),
        Input("results_treeview", "checked"),
        Input("results_table_columns_checklist", "value"),
        Input("energy_unit_select", "value"),
        State("complete_results_dict_store", "data"),
        prevent_initial_call=True,
    )(update_table_values)

    app.callback(
        Output("download_table_button", "children"),
        Input("download_table_button", "n_clicks"),
        State("results_table", "data"),
        prevent_initial_call=True,
    )(download_table_data)

    app.callback(
        Output("detailed_results_screen_header", "children"),
        Output("detailed_results_store", "data"),
        Output("detailed_results_screen_fade", "is_in"),
        Input("results_table", "selected_rows"),
        State("results_table", "data"),
        State("complete_results_dict_store", "data"),
        prevent_initial_call=True,
    )(update_detailed_screen_header)

    app.callback(
        Output("speck_slider", "max"),
        Output("speck_slider", "value"),
        Output("speck_slider", "step"),
        Output("speck_slider", "marks"),
        Output("speck_slider_fade", "is_in"),
        Input("detailed_results_store", "data"),
        prevent_initial_call=True,
    )(update_xyz_slider)

    app.callback(
        Output("speck", "data"),
        Input("speck_slider", "value"),
        State("detailed_results_store", "data"),
        prevent_initial_call=True,
    )(update_xyz_data)

    app.callback(
        Output("energy_convergence_plot", "figure"),
        Output("energy_convergence_plot_fade", "is_in"),
        Input("detailed_results_store", "data"),
        Input("energy_unit_select", "value"),
        prevent_initial_call=True,
    )(update_energy_convergence_plot)

    app.callback(
        Output("simulated_ir_spectrum_graph", "figure"),
        Output("simulated_ir_spectrum_graph_fade", "is_in"),
        Input("detailed_results_store", "data"),
        prevent_initial_call=True,
    )(update_simulated_ir_spectrum)

    return app
