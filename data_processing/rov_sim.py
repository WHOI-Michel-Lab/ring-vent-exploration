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


class CaptureHolder():
    def __init__(self, video_dir):
        self.cap = None
        self.file = None
        self.seconds = None
        self.video_dir = video_dir
        
    def set_file(self, file):
        if file == self.file:
            return
        else:
            self.file = file
            self.cap = cv2.VideoCapture(os.path.join(self.video_dir, file))
            
    def seek(self, seconds):
        self.seconds = seconds
        self.cap.set(cv2.CAP_PROP_POS_MSEC, seconds*1000)
        
    def fast_forward(self):
        self.seek(self.seconds + 5)

    def rewind(self):
        self.seek(self.seconds - 5)


    def get_image(self, file, seconds):
        # gives a plotly figure of the specified image
        self.set_file(os.path.join(self.video_dir, file))

        self.seek(seconds)

        ret, frame = self.cap.read()
        
        if not ret:
            raise ValueError("Image not found")
        
        
    #     CV2 seems to default to ordering the channels unusually
    #     This orders them as rgb so that plotly understands it
        return px.imshow(cv2.merge(cv2.split(frame)[::-1]))




def run_server(fig, timeline, near_vent, start_end_by_file, cap):

    columns_of_interest = near_vent.columns

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
            dcc.Loading(children = [
                dcc.Graph(id='camera'),
            ]),
             
             html.Pre(id='sensor_display', style = styles['pre'])
        ], style = styles['display_wrapper']),
        
        html.Div(children = [
            dcc.Graph(id = 'spatial', figure=fig),
            dcc.Graph(id='timeline', figure=timeline)
        ], style = styles['display_wrapper']),
        html.Div(children = [
            'Unix Time: ',
            dcc.Input(value=0, id='frame_selector', style={'margin': 'auto'}), 
        ]),
        

        
    ], style={})#'display':'flex', 'flex-direction':'row'})
        
    # SCRIPTING
    @app.callback(
        Output(component_id = 'camera', component_property='figure'),
        # Input('spatial', 'clickData')
        Input('timeline', 'clickData')
    )
    def set_camera(node_clicked):
        custom_data = node_clicked['points'][0]['customdata']
        timestamp = data.loc[custom_data]['unix_time']
        start = start_end_by_file[data.iloc[custom_data]['video_file']][0]
        seek_dist = timestamp - start
        return cap.get_image(data.iloc[custom_data]['video_file'], seek_dist)
        
        
    #     return px.imshow(im_by_time[timestamp])
    #     return px.imshow(video_extraction.decompress_image(im_by_time[timestamp]))


    @app.callback(
        Output(component_id = 'frame_selector', component_property='value'),
        # Input('spatial', 'clickData')
        Input('timeline', 'clickData')
    )
    def set_frame(node_clicked):
        print(node_clicked)
        return data.loc[node_clicked['points'][0]['customdata']]['unix_time']



    @app.callback(
        Output(component_id = 'sensor_display', component_property='children'),
        # Input('spatial', 'clickData')
        Input('timeline', 'clickData')
    )
    def set_sensor_readout(node_clicked):
        node_index = node_clicked['points'][0]['customdata']
        data = near_vent.loc[node_index][columns_of_interest].to_dict()
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
        "--video_dir",
        required=True,
        type=str,
        help="Directory with video related to the given data"
    )
    parser.add_argument(
        "--mesh_file",
        required=True,
        type=str,
        help="An unlabeled tsv file with column 1 latitude column 2 longitude and column 3 depth"
    )

    args = parser.parse_args()
    return args



if __name__ == '__main__':

    args = get_args()

    start_end_by_file = get_frames(args.video_dir)

    data = pd.read_csv(args.data_file)
            
    cap = CaptureHolder(args.video_dir) # This keeps track of our video reading

    # Set up point coloring
    data['color'] = data.unix_time.apply(time_to_file, start_end_by_file=start_end_by_file, return_int=True)
    data['video_file'] = data.unix_time.apply(time_to_file, start_end_by_file=start_end_by_file)

    # Get Mesh
    mesh = utils.get_mesh(args.mesh_file, 1000)
    mesh.opacity = .3
    mesh.hoverinfo = "skip"

    # TODO: This is specific to ring vent
    near_vent = data.loc[np.where((data.depth < -1700) & (pd.notna(data.video_file)))]
    colors = ['rgba(0, 0, 0, .001)', *px.colors.DEFAULT_PLOTLY_COLORS]
    # TODO: This isn't robust to a larger number of input files, need a larger color array
    near_vent['rgb'] = near_vent.color.apply(lambda i: colors[int(i)] if pd.notna(i) else colors[0])
    
    scatterplot = go.Scatter3d(
        x=near_vent.northing,
        y=near_vent.easting,
        z=near_vent.depth,
        text = near_vent.unix_time,#data[pd.notna(data.video_file)].text,
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
        mode="markers",
        marker=dict(
            color=near_vent.rgb,
        ),
        customdata=near_vent.index
    )
    timeline = go.Figure(data = [timeline_plot])

    # timeline = px.scatter(
    #     near_vent, 
    #     x="unix_time", 
    #     y = [0]*len(near_vent), 
    #     color = "rgb",
    #     color_discrete_map="identity"
    # )

    run_server(fig, timeline, near_vent, start_end_by_file, cap)