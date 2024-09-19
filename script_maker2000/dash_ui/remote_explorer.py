import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
import dash_treeview_antd as dta
from script_maker2000.dash_ui.config_maker_ui import create_new_input
from script_maker2000.dash_ui.remote_explorer_calls import (
    print_selected_path,
    return_selected_path,
    check_local_zip_file,
    get_local_paths,
    disable_button_start_interval,
    _get_live_updates,
    _submit_job,
    _get_remote_paths,
    _check_remote_dir,
)

default_style = {"margin": "10px", "width": "100%"}


def create_manager_layout():

    remote_explorer_layout = create_remote_explorer_layout("remote")
    local_explorer_layout = create_remote_explorer_layout("local")
    submission_layout = create_job_submission_layout()

    layout = dbc.Row(
        children=[
            dbc.Col(
                children=[
                    local_explorer_layout,
                ],
                width=3,
                style={"padding-right": "10px"},
            ),
            dbc.Col(
                children=[
                    remote_explorer_layout,
                ],
                width=3,
            ),
            dbc.Col(
                children=[
                    submission_layout,
                ],
                width=5,
                style={"padding-left": "10px"},
            ),
        ]
    )

    return layout


def create_remote_explorer_layout(mode):

    if mode == "remote":
        header_text = [
            "This is the remote explorer.",
            html.Br(),
            "Select the directory where you want to start the calculation.",
            html.Br(),
            "You can also select a workspace to start from.",
            html.Br(),
            "Either write 'workspaces' or a workspace id to start from there.",
        ]
        input_id = "remote_path_input"
        input_label = "Enter remote path:"
        input_value = ""
        input_placeholder = "Remote dir or path"

    if mode == "local":
        header_text = [
            "This is the local explorer.",
            html.Br(),
            "Select the local zipfile you want to submit.",
        ]
        input_id = "local_path_input"
        input_label = "Enter local path:"
        input_value = "."
        input_placeholder = "Local dir or path"

    layout = dbc.Row(
        children=[
            # explanation text for the user
            html.P(
                header_text,
                style={"margin": "10px", "width": "100%", "height": "100px"},
            ),
            create_new_input(input_label, input_value, input_id, input_placeholder),
            # text field to show wich path is selected
            html.P(
                id=f"{mode}_path_output",
                children="No path selected yet.",
                style={"margin": "10px", "width": "100%", "height": "50px"},
            ),
            dbc.Button(
                "Search path",
                id=f"{mode}_explorer_submit",
                style={"margin": "10px", "width": "80%", "align": "center"},
            ),
            # checkable, checked, data, expanded, id, multiple, selected
            dcc.Loading(
                children=[
                    dta.TreeView(
                        multiple=False,
                        checkable=False,
                        id=f"{mode}_tree_view",
                        data=None,
                    ),
                ]
            ),
        ],
    )

    return layout


def create_job_submission_layout():
    placeholder_local = "Select files to submit."
    placeholder_remote = "Select a parent dir  (Use / to add a sub directory.)"

    layout = dbc.Row(
        children=[
            html.H3("Job submission", style=default_style),
            html.P(
                [
                    "To submit a job you should have collected the input files in the Config tab."
                    + " This will create a zip file.",
                    html.Br(),
                    "Use the file explorer on the left to select the zip of the job you want to submit.",
                    html.Br(),
                    "Use the file explorer on the right to select the parent directory for the calculation.",
                ],
                style=default_style,
            ),
            create_new_input(
                "Select the zip file of your calculation. (See Config tab)",
                "",
                "valid_input_file",
                placeholder_local,
                True,
            ),
            create_new_input(
                "Select the parent dir for your calculation.",
                "",
                "valid_target_dir",
                placeholder_remote,
                readonly=False,
                debounce=True,
            ),
            html.P(
                [
                    "If these are correct, press the submit button to start a new calculation.",
                    html.Br(),
                    "After starting a job you need to select a new zip file for the button to be enabled again.",
                    html.Br(),
                    "Please note that submitting the same job twice will most likely cause something to fail.",
                ],
                style=default_style,
            ),
            dbc.Button(
                "Submit job", id="submit_new_job", style=default_style, disabled=True
            ),
            dcc.Interval(
                id="job_status_interval",
                max_intervals=0,
                interval=1.5 * 1000,  # in milliseconds
            ),
            html.Div(id="empty_div_explorer", style={"display": "none"}),
            # dcc.Loading(
            dbc.Textarea(
                id="job_output",
                style={"margin": "10px", "width": "100%", "height": "400px"},
                readOnly=True,
            ),
            # ),
        ]
    )
    return layout


def add_callbacks_remote_explorer(app, remote_connection):

    def get_remote_paths(
        n_clicks,
        path,
    ):

        return _get_remote_paths(n_clicks, path, remote_connection)

    def get_live_updates(
        n_intervals,
        target_dir,
    ):
        """This function will check the output file for the job status and update the textarea.

        Args:
            n_intervals (int): Value of the button to trigger the function.
            target_dir (str): Remote target dir for the calculation.
        """
        return _get_live_updates(n_intervals, target_dir, remote_connection)

    def submit_job(n_clicks, input_file, target_dir):
        """This function will copy the input file to the target dir and start the calculation.
        Will also start the interval for live updates.

        Args:
            n_clicks (int): Value of the button to trigger the function.
            input_file (str): Local input file to copy to the target dir.
            target_dir (str): Remote target dir for the calculation.
        """

        return _submit_job(n_clicks, input_file, target_dir, remote_connection)

    def check_remote_dir(target_dir):
        return _check_remote_dir(target_dir, remote_connection)

    app.callback(
        Output("job_output", "value"),
        Output("job_status_interval", "max_intervals", allow_duplicate=True),
        Input("job_status_interval", "n_intervals"),
        State("valid_target_dir", "value"),
        prevent_initial_call=True,
    )(get_live_updates)

    app.callback(
        Output("submit_new_job", "disabled", allow_duplicate=True),
        Output("job_status_interval", "n_intervals", allow_duplicate=True),
        Input("submit_new_job", "n_clicks"),
        prevent_initial_call=True,
    )(disable_button_start_interval)

    app.callback(
        Output(
            "empty_div_explorer", "children", allow_duplicate=True
        ),  # start the interval for live updates
        Input("submit_new_job", "n_clicks"),
        State("valid_input_file", "value"),
        State("valid_target_dir", "value"),
        prevent_initial_call=True,
    )(submit_job)

    app.callback(
        Output("local_tree_view", "data"),
        Input("local_explorer_submit", "n_clicks"),
        State("local_path_input", "value"),
        prevent_initial_call=False,
    )(get_local_paths)

    app.callback(
        Output("remote_tree_view", "data"),
        Input("remote_explorer_submit", "n_clicks"),
        State("remote_path_input", "value"),
        prevent_initial_call=False,
    )(get_remote_paths)

    app.callback(
        Output("remote_path_output", "children"),
        Input("remote_tree_view", "selected"),
        prevent_initial_call=True,
    )(print_selected_path)

    app.callback(
        Output("local_path_output", "children"),
        Input("local_tree_view", "selected"),
        prevent_initial_call=True,
    )(print_selected_path)

    app.callback(
        Output("valid_input_file", "value"),
        Input("local_tree_view", "selected"),
        prevent_initial_call=True,
    )(return_selected_path)

    app.callback(
        Output("valid_target_dir", "value"),
        Input("remote_tree_view", "selected"),
        prevent_initial_call=True,
    )(return_selected_path)

    app.callback(
        Output("valid_input_file", "valid"),
        Output("valid_input_file", "invalid"),
        Output("submit_new_job", "disabled", allow_duplicate=True),
        Input("valid_input_file", "value"),
        prevent_initial_call=True,
    )(check_local_zip_file)

    app.callback(
        Output("valid_target_dir", "valid"),
        Output("valid_target_dir", "invalid"),
        Output("submit_new_job", "disabled", allow_duplicate=True),
        Input("valid_target_dir", "value"),
        prevent_initial_call=True,
    )(check_remote_dir)
    return app
