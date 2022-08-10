import utils
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px


def scott_time_to_unix(scott_time):
    """The mass spec data has an uncommon timestamp that 
    seems to be expressed in days since some unknown date. 
    This convertes to seconds and takes off enough seconds to convert
    to seconds from the unix epoch. This was determined from a known 
    scott time and datetime overlap"""
    return scott_time * 24*60*60 - 62167287600.0

def get_long_data(data_dir):
    """get_long_data parses the mass spec data into 
    a 'long' format, where the columns are time, mass_spec, and mass.
    In other words, each row is a reading of a particular mass at a particular time"""
    files = os.listdir(data_dir)
    files.sort()

    split_data = [pd.read_csv(os.path.join(data_dir, filename)) for filename in files]


    long_split = []
    for data in split_data:
        data = data.melt(id_vars=data.columns[0], var_name='time', value_name='mass_spec')
        data['mass'] = data[data.columns[0]]
        data = data.drop(columns=data.columns[0])
        long_split.append(data)

    long_data = pd.concat(long_split, ignore_index=True)


    long_data['time'] = long_data['time'].astype('float64')
    long_data['time'] = long_data.time.apply(scott_time_to_unix)
    return long_data

def get_wide_data(data_dir):
    """get_wide_data parses mass spec data into 
    a wide format. There are columns for time, and each of the masses 
    measured by the mass spectrometry. Each row is a reading across all 
    masses at a specific time."""
    files = os.listdir(data_dir)
    files.sort()

    split_data = [pd.read_csv(os.path.join(data_dir, filename), header=None) for filename in files]
    # The headers are stored as the first column of every file
    # With a placeholder 0.0 at the top. So we are taking 
    # Everything but the 0 in the first column of the first file
    header = ['time'] + split_data[0][0][1:].tolist()

    transposed_data = []
    for data in split_data:
        data = data.drop(columns=[0])
        data = data.transpose()
        data.columns = header
        transposed_data.append(data)

    combined = pd.concat(transposed_data, ignore_index=True)
    combined['time'] = combined.time.apply(scott_time_to_unix)
    
    return combined



def get_args():
    """Basic argument parsing.
    for example:
        python mass_spec_utils.py --data_dir ../data/J2-1393 --time 0"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--data_dir', 
        type=str, 
        required=True, 
        help="A directory of mass_spec CSVs with the first column storing mass, and headers representing time"
    )

    parser.add_argument(
        '--time',
        type=float,
        required=True,
        help="Will show a cutout of mass spec at closest point to given time."
    )
    

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    wide_data = get_wide_data(args.data_dir)

    utils.get_row_by_value(wide_data, 'time', args.time)[1:].plot()
    plt.show()


