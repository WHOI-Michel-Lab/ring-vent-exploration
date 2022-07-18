import utils
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px




def get_long_data(data_dir):
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
    return long_data

def get_wide_data(data_dir):
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
    return combined



def get_args():
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


