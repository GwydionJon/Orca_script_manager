import dash_bootstrap_components as dbc
import datetime
import json
from pathlib import Path
from dash import html, dcc, Input, Output, State, dash_table
from script_maker2000.dash_ui.slurm_watch_calls import get_sacct_output

default_style = {"margin": "10px", "width": "100%"}


def create_slurm_watcher_layout():

    # important options for the sacct command
    # format - multi select radio or something like that
    # start/end date - date picker
    # job id - text input
    sacct_dict = Path(__file__).parent / "sacct_options.json"
    with open(sacct_dict, "r", encoding="utf-8") as f:
        sacct_dict = json.load(f)

    # Time Picker Section
    time_picker = dbc.Col(
        [
            dbc.Row(html.H4("Pick a time range to search for jobs:")),
            dbc.Row(
                dcc.DatePickerRange(
                    id="date_picker_range",
                    start_date_placeholder_text="Start Date",
                    start_date=datetime.date.today(),
                    end_date=datetime.date.today(),
                    end_date_placeholder_text="End Date",
                    calendar_orientation="horizontal",
                    display_format="YYYY-MM-DD",
                    style=default_style,
                    clearable=False,
                )
            ),
            dbc.Row(
                dcc.RangeSlider(
                    id="time_slider",
                    min=0,
                    max=24,
                    step=1,
                    marks={i: str(i) for i in range(0, 25)},
                    value=[0, 24],
                    allowCross=False,
                )
            ),
        ],
        style=default_style,
    )

    # Format Option Picker Section
    format_option_picker = dbc.Col(
        [
            dbc.Row(html.H4("Pick which entries to display:")),
            dbc.Row(
                dbc.Checklist(
                    id="format_option_picker",
                    options=[
                        {"label": value, "value": value}
                        for value in sacct_dict["sacct_format"]
                    ],
                    value=[
                        "JobID",
                        "JobName",
                        "State",
                        "ExitCode",
                        "Elapsed",
                        "Start",
                        "End",
                    ],
                    style=default_style,
                    inline=True,
                )
            ),
        ],
        style=default_style,
    )

    # Update Button Section
    slurm_update_button = dbc.Col(
        [
            dbc.Row(
                dbc.Button(
                    "Get Slurm Output",
                    id="slurm_update_button",
                    color="primary",
                    style={"margin": "10px", "width": "20%"},
                ),
            ),
        ],
    )

    # Table Explanation Section
    table_explanation = dbc.Col(
        [
            dbc.Row(
                [
                    html.H4("Slurm Output:"),
                    html.Br(),
                    html.P(
                        "This table shows the output of the sacct command. "
                        "You sort the table by clicking on the column headers."
                    ),
                    html.Br(),
                    html.P(
                        "You can also filter the table by typing in the filter boxes at the top of the table."
                    ),
                    html.Br(),
                    html.P(
                        [
                            "For more information about filtering syntax check the ",
                            html.A(
                                "dash wiki.",
                                href="https://dash.plotly.com/datatable/filtering",
                                target="_blank",
                            ),
                        ]
                    ),
                    html.Br(),
                    html.P("The most relevant state values are:"),
                    html.Br(),
                    html.P(
                        "CANCELLED, COMPLETED, OUT_OF_MEMORY, PENDING, RUNNING, TIMEOUT"
                    ),
                ]
            )
        ]
    )

    # Slurm Table Section
    slurm_table = dash_table.DataTable(
        id="slurm_table",
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        style_table={"overflowX": "auto", "overflowY": "auto", "height": "500px"},
    )

    # Main Layout
    main_layout = dbc.Col(
        [
            dcc.Store(id="sacct_output"),
            dbc.Row(html.H2("Slurm Watcher")),
            dbc.Row(
                [
                    dbc.Col(time_picker, width=3),
                    dbc.Col(format_option_picker, width=9),
                ]
            ),
            dbc.Row(slurm_update_button),
            dbc.Row(table_explanation),
            dbc.Row(slurm_table),
        ],
        style=default_style,
    )

    return main_layout


def add_callbacks_slurm_watcher(app, remote_connection):

    def get_sacct_output_callback(
        n_clicks, start_date, end_date, time_range, format_entries
    ):
        return get_sacct_output(
            n_clicks,
            start_date,
            end_date,
            time_range,
            format_entries,
            remote_connection,
        )

    app.callback(
        Output("slurm_table", "data"),
        Output("slurm_table", "columns"),
        [
            Input("slurm_update_button", "n_clicks"),
        ],
        [
            State("date_picker_range", "start_date"),
            State("date_picker_range", "end_date"),
            State("time_slider", "value"),
            State("format_option_picker", "value"),
        ],
        prevent_initial_call=True,
    )(get_sacct_output_callback)

    return app
