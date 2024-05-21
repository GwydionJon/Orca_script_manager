import dash_bootstrap_components as dbc

# import dash_renderjson
# import dash_cytoscape as cyto
# import json
from dash import html  # , dcc, Input, Output, State, MATCH, ALL

# from pathlib import Path

default_style = {"margin": "10px", "width": "100%"}


def create_slurm_watcher_layout():
    main_layout = dbc.Col(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Slurm Watcher"),
                            html.P("This tab is under construction"),
                        ],
                        width=12,
                    ),
                ]
            )
        ],
    )
    return main_layout


def add_callbacks_slurm_watcher(app, remote_connection):
    return app
