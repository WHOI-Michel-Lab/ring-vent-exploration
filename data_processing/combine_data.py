from scipy.interpolate import interp1d
import utils
import pandas as pd
import utm
import os
import argparse

# This can be changeable for whatever 
# DATA_DIR = "../data/J2-1393"

extensions = ['csv', 'ct2', 'oos', 'obs']

def get_file_names(data_dir):
    # Each "file format" has these days. I want the prefix 
    # that works for each, in order, without the suffix, so I can
    # collect the corresponding set from each group and then merge later
    files = os.listdir(f"{data_dir}/csv")
    files.sort()

    # There are some datafiles that begin ._<date> that seem to not be openable
    # This prevents them from messing up the processing
    return [filepath.split('.')[0] for filepath in files if not filepath.startswith('.')]

def aggregate_data(data_dir, file_day):
    file_paths = {
        extension:f"{data_dir}/{extension}/{file_day}.{extension.upper()}" 
        for extension 
        in extensions
    }

    raw_data = {
        ext : utils.load_from_file(path)
        for (ext, path)
        in file_paths.items()
    }

    # Give a standardized time for each datastream to allow for joining later
    raw_data['ct2']['unix_time'] = raw_data['ct2'].apply(
        lambda row: utils.date_time_to_unix(row['date'], row['time']), 
        axis=1
    )

    raw_data['oos']['unix_time'] = raw_data['oos'].apply(
        lambda row: utils.date_time_to_unix(row['date'], row['time']), 
        axis=1
    )

    raw_data['obs']['unix_time'] = raw_data['obs'].apply(
        lambda row: utils.date_time_to_unix(row['date'], row['time']), 
        axis=1
    )

    raw_data['csv']['unix_time'] = raw_data['csv']['time(seconds since Jan 1 1970)']

    combined_data = raw_data['csv']
    combined_data.index = combined_data.unix_time

    # We can first merge the two with the same logging frequency    
    raw_data['ct2'].index = raw_data['ct2'].unix_time

    combined_data = pd.merge_asof(
        combined_data, 
        raw_data['ct2'], 
        left_index=True, 
        right_index=True
    )

    # We can then project the data from the other data streams onto the 
    # Over-arching datastream
    interp_obs = interp1d(
        raw_data['obs'].unix_time, 
        raw_data['obs'].obs, 
        fill_value='extrapolate'
    )

    interp_oos = interp1d(
        raw_data['oos'].unix_time, 
        raw_data['oos'].oxygen, 
        fill_value='extrapolate'
    )

    combined_data['obs_proj'] = interp_obs(combined_data['time(seconds since Jan 1 1970)'])
    combined_data['oxygen_proj'] = interp_oos(combined_data['time(seconds since Jan 1 1970)'])



    combined_data['source'] = file_day

    return combined_data



def get_csv_and_navest(data_dir , clean_up = True):
    days = get_file_names(data_dir)
    # We only take the files after the first because not
    # all datastreams seem to have been recording for that 
    # first day.
    dfs = [aggregate_data(data_dir, day) for day in days[1:]]
    combined = pd.concat(dfs, ignore_index=True)



    # Getting the renav data:
    renav_file = f"{data_dir}/navest/J2-1393_renav.ppi"
    renav_columns = ["date", "time", "lat", "lon", "depth", "ua", "ub", "uc", "ud"]

    # The renav data is space seperated so we're just going to split each line
    # to get the proper columns out.
    renav_data = pd.read_csv(renav_file, header=None, names=['lump'])
    renav_data[renav_columns] = renav_data.lump.str.split(' ').tolist()

    renav_data["unix_time"] = renav_data.apply(
        lambda row: utils.date_time_to_unix(row['date'], row['time']), 
        axis=1
    ).tolist()

    full_df = pd.merge_asof(combined, renav_data, left_on='unix_time_x', right_on='unix_time')

    if clean_up:
        full_df.drop([
            'X local(m)', 'Y local(m)', 'X UTM(m)', 'Y UTM(m)', 'UTMZone', 'depth(m)',
            'altitude(m)', 'octans heading(deg)', 'octans pitch(deg)',
            'octans roll(deg)', 'crossbow heading(deg)', 'crossbow pitch(deg)',
            'crossbow roll(deg)', 'maggie x', 'maggie y', 'maggie z',
            'maggie total', 'conductivity_x',  'temperature(deg C)', 'depth(m)_2',
            'salinity_x', 'sound velocity', 'pressure_x', 'lss gain', 'lss backscatter', 'None',
            'unix_time_x', 'date_x', 'date_y'
        ], axis=1, inplace=True)

        full_df = full_df.astype({
           col:'float'
            for col 
            in [
                'temperature', 'salinity_y', 'conductivity_y', 
                'pressure_y', 'obs_proj', 'oxygen_proj', 'depth',
                'lat', 'lon']

        })


        # We will add a useful preprocessing step, by 
        # converting latlon into utm coords
        full_df[['northing', 'easting']] = full_df.apply(
            lambda row: utm.from_latlon(
                row['lat'], 
                row['lon']
            )[:2], 
            axis=1
        ).tolist()


    return full_df


def get_mass_spec(dir):
    files = os.listdir(dir)
    files.sort()

    split_data = [pd.read_csv(os.path.join(dir, filename), header=None) for filename in files]

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

    return pd.concat(transposed_data, ignore_index=True)


def get_methane_data(path, drop_duplicate=True):
    """
    Expects a path to a methane data csv with timestamp, 
    fundamental, ringdown, and methane columns
    
    There seems to be many duplicate rows with not even slight variation. 
    We will drop duplicates by time, by default, drop_duplicate=False to disable
    
    """
    data = pd.read_csv(path)
    data['unix_time'] = data.timestamp.str.split(' ').apply(lambda x: utils.date_time_to_unix(x[0], x[1]))

    if drop_duplicate:
        data = data.drop_duplicates('unix_time')

    return data


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_dir', required=True, type=str, help="Directory with J2-1393 sensor data")
    parser.add_argument('--methane_path', required=True, type=str, 
        help="Path to csv containing timestamp, fundamental, ringdown, and methane data")

    parser.add_argument('--output_file', required=True, type=str, help="Where to save resulting csv")


    return parser.parse_args()



if __name__ == '__main__':
    args = get_args()

    data = get_csv_and_navest(args.data_dir)
    methane_data = get_methane_data(args.methane_path)


    data = pd.merge_asof(data, methane_data, left_on="unix_time", right_on="unix_time")
    data.to_csv(args.output_file, index=False)

