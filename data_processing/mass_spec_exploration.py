import cv2
import matplotlib.pyplot as plt
import sys
import pandas as pd
import os
import numpy as np
import json
import argparse

import plotly.graph_objects as go
import plotly.express as px

from dash import Dash
from dash import html, dcc
from dash.dependencies import Input, Output

# Custom files
import video_extraction
import combine_data
import utils
import mass_spec_utils 



def get_frames(video_dir):

    start_end_by_file = {}

    for filename in os.listdir(video_dir):
        if filename.startswith('.'):
            continue
            
        path = os.path.join(video_dir, filename)
        
        starttime = video_extraction.get_start_time(path)
        
        cap = cv2.VideoCapture(path)
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count/fps

        approx_endtime = starttime + duration
        
        start_end_by_file[filename] = (starttime, approx_endtime)

    return start_end_by_file


def time_to_file(time, start_end_by_file, return_int=False):
    """Given a time, and a map from file to 
    start and end time, return which file
    time belongs in. (None if none)"""
    index = 0
    for file, (start, end) in start_end_by_file.items():
        index += 1
        if start <= time and time <= end:
            if return_int:
                return index
            return file
    return None


def run_server(fig, timeline, near_vent, mass_spec):

    app = Dash(__name__)


    styles = {
        'pre': {
            'border': 'thin lightgrey solid',
            'overflowX': 'scroll',
            'overflowY': 'scroll',
            "height": "450px",
    #         "margin": "auto",
            "margin-top": "15px",
    #         'height': '450px'
        },
        'display_wrapper': {
            'display': 'flex',
            'flex-direction': 'row',
            'justify-content': 'space-around',
            
        }
    }

        
    app.layout = html.Div(children=[

        html.Div(children = [
            dcc.Graph(id = "mass_spec"),
           
            html.Pre(id='sensor_display', style = styles['pre'])
        ], style = styles['display_wrapper']),
        
        html.Div(children = [
            dcc.Graph(id = 'spatial', figure=fig),
            dcc.Graph(id = 'timeline', figure=timeline)
        ], style=styles['display_wrapper'])
        

        
    ], style={})
        
    # SCRIPTING
    @app.callback(
        Output(component_id = 'mass_spec', component_property='figure'),
        Input('timeline', 'clickData')
    )
    def set_mass_spec(node_clicked):
        # Get time of point
        custom_data = node_clicked['points'][0]['customdata']
        timestamp = data.loc[custom_data]['unix_time']

        row = utils.get_row_by_value(mass_spec, "time", timestamp)
        row_time = row[0]

        time_diff = abs(timestamp - row_time)

        return px.line( x = row.index[1:], y = row[1:].tolist(), )
        
        
    @app.callback(
        Output(component_id = 'sensor_display', component_property='children'),
        Input('timeline', 'clickData')
    )
    def set_sensor_readout(node_clicked):
        node_index = node_clicked['points'][0]['customdata']
        data = near_vent.loc[node_index].to_dict()
        print(data)
        return json.dumps(data, indent=2)
    

    app.run(port="8002", debug=True)



def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_file", 
        required=True,
        type=str, 
        help="Expects a labeled csv file with at least columns labeled 'unix_time', 'northing', 'easting'"
    )
    parser.add_argument(
        "--mesh_file",
        required=True,
        type=str,
        help="An unlabeled tsv file with column 1 latitude column 2 longitude and column 3 depth"
    )
    parser.add_argument(
        "--mass_spec_dir",
        required=True,
        type=str,
        help="The directory storing mass spectrometry csv files."
    )
    parser.add_argument(
        '--subsample_factor',
        type=int,
        default=1,
        help="The factor by which to subsample data. (E.g. if factor is 5, 1/5 of points are taken)"

    )

    args = parser.parse_args()
    return args



if __name__ == '__main__':

    args = get_args()

    data = pd.read_csv(args.data_file)

    mass_spec = mass_spec_utils.get_wide_data(args.mass_spec_dir)            

    # Get Mesh
    mesh = utils.get_mesh(args.mesh_file, 1000)
    mesh.opacity = .3
    mesh.hoverinfo = "skip"


    # TODO: This is specific to ring vent
    near_vent = data.loc[(data.depth < -1700), :]
    colors = ['rgba(0, 0, 0, .001)', *px.colors.DEFAULT_PLOTLY_COLORS]
    near_vent['rgb'] = near_vent.unix_time

    near_vent = near_vent[near_vent.index % args.subsample_factor == 0]

    
    scatterplot = go.Scatter3d(
        x=near_vent.northing,
        y=near_vent.easting,
        z=near_vent.depth,
        text = near_vent.unix_time,
        mode='markers',
        marker=dict(
            color=near_vent.rgb,
        ),
        customdata = near_vent.index
    )

    PLOT_MESH = True
    fig = go.Figure(data = ([mesh, scatterplot] if PLOT_MESH else [scatterplot]))

    timeline_plot = go.Scatter(
        x=near_vent.unix_time,
        y=[0]*len(near_vent),
        text = near_vent.unix_time,
        mode='markers',
        marker=dict(
            color=near_vent.rgb,
        ),
        customdata = near_vent.index
    )
    timeline = go.Figure(data=[timeline_plot])
    


    run_server(fig, timeline, near_vent, mass_spec)