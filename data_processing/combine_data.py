from scipy.interpolate import interp1d
import utils
import pandas as pd
import utm
import os

# This can be changeable for whatever 
DATA_DIR = "../data/J2-1393"

extensions = ['csv', 'ct2', 'oos', 'obs']

def get_file_names(data_dir = DATA_DIR):
    # Each "file format" has these days. I want the prefix 
    # that works for each, in order, without the suffix, so I can
    # collect the corresponding set from each group and then merge later
    files = os.listdir(f"{data_dir}/csv")
    files.sort()
    return [filepath.split('.')[0] for filepath in files]

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


    # We will add a useful preprocessing step, by 
    # converting latlon into utm coords
    combined_data[['northing', 'easting']] = combined_data.apply(
        lambda row: utm.from_latlon(
            row['latitude(deg)'], 
            row['longitude(deg)']
        )[:2], 
        axis=1
    ).tolist()

    combined_data['source'] = file_day

    return combined_data



def get_csv_and_navest(data_dir = DATA_DIR):
    days = get_file_names()
    # We only take the files after the first because not
    # all datastreams seem to have been recording for that 
    # first day.
    dfs = [aggregate_data(DATA_DIR, day) for day in days[1:]]
    combined = pd.concat(dfs, ignore_index=True)

    # combined.drop([
    #     'X local(m)', 'Y local(m)', 'X UTM(m)', 'Y UTM(m)', 'UTMZone', 'depth(m)',
    #     'altitude(m)', 'octans heading(deg)', 'octans pitch(deg)',
    #     'octans roll(deg)', 'crossbow heading(deg)', 'crossbow pitch(deg)',
    #     'crossbow roll(deg)', 'maggie x', 'maggie y', 'maggie z',
    #     'maggie total', 'conductivity_x',  'temperature(deg C)', 'depth(m)_2',
    #     'salinity_x', 'sound velocity', 'pressure_x', 'lss gain', 'lss backscatter', 'None',
    #     'unix_time_x', 'date_x', 'date_y'
    # ], axis=1, inplace=True)


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

    return pd.merge_asof(combined, renav_data, left_on='unix_time_x', right_on='unix_time')




if __name__ == '__main__':
    pass