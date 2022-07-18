import pandas as pd
import utm
import plotly.express as px
import plotly.graph_objects as go
import datetime
from bisect import bisect_left

MESH_PATH = "../data/ring_depth.csv"

def get_mesh(path, step, use_utm=True):
    """Given the path to a tsv 
    file with the longitude, latitude, and depth,
    returns a plotly mesh object.
    
    step : subsample at regular step sized intervals to speed up plotting
    use_utm : determines what coordinate system to use for the mesh. Defaults to 
            converting to utm (meters)"""

    ring_depth = pd.read_csv(path, header=None, names = ['lon', 'lat', 'depth'], sep='\t')
    usable_ring_depth = ring_depth[pd.notna(ring_depth.depth)]
    usable_ring_depth = usable_ring_depth.reset_index(drop=True)

    subsample_ring_depth = usable_ring_depth.iloc[list(range(0, len(usable_ring_depth), step))].reset_index(drop=True)



    # If we're not converting to 
    # utm, then we're good 

    if not use_utm: 
        return go.Mesh3d(
            x=subsample_ring_depth.lon, 
            y=subsample_ring_depth.lat, 
            z=subsample_ring_depth.depth, 
            opacity=.5
        )

    # Convert to northing and easting from lat-lon
    subsample_ring_depth[['northing', 'easting']] = subsample_ring_depth.apply(lambda row: utm.from_latlon(row['lat'], row['lon'])[:2], axis=1).tolist()
    
    return go.Mesh3d(x=subsample_ring_depth.northing, y=subsample_ring_depth.easting, z=subsample_ring_depth.depth, opacity=.5)


"""
renav:
NAV_COLUMNS = ["date", "time", "lat", "lon", "depth", "ua", "ub", "uc", "ud"]
"""


def load_sensor_file(path, fields, explode_fields):
    """
    Parse data from a particular sensor stream

    path : path to the file to read
    fields : names of the columns to assign
    explode_fields :  list of tuples of fields to split 
                        along with the names of new fields
    """

    data = pd.read_csv(path, header = None, names = fields, comment="#")

    # Some of the data streams don't include commas where they 
    # should, so it's necessary to split them up after read-in
    for field, new_names in explode_fields:
        data[new_names] = data[field].str.split().tolist()
    return data

SCIENCE_VAR = ["CT2", "OBS", "OOS", "CSV"]

RAW_COLUMNS = {}
RAW_COLUMNS['OBS'] = ['lump1']
RAW_COLUMNS['CT2'] = ['lump1', "conductivity", "pressure", "salinity", "sound_speed"]
RAW_COLUMNS['OOS'] = ['lump1']
RAW_COLUMNS['CSV'] = ['Vehicle', 'year', 'month', 'day', 'hour', 'minutes', 'seconds', 'time(seconds since Jan 1 1970)', 'latitude(deg)', 'longitude(deg)', 'X local(m)', 'Y local(m)', 'latitude origin(deg)', 'longitude origin(deg)', 'X UTM(m)', 'Y UTM(m)', 'UTMZone', 'depth(m)', 'altitude(m)', 'octans heading(deg)', 'octans pitch(deg)', 'octans roll(deg)', 'crossbow heading(deg)', 'crossbow pitch(deg)', 'crossbow roll(deg)', 'maggie x', 'maggie y', 'maggie z', 'maggie total', 'conductivity', 'temperature(deg C)', 'depth(m)_2', 'salinity', 'sound velocity', 'pressure', 'lss gain', 'lss backscatter', "None"]

EXPAND_COLUMNS = {}
EXPAND_COLUMNS['OBS'] = [('lump1', ["sensor1", "date", "time", "sensor2", "obs", "_1", "_2", "_3"])]
EXPAND_COLUMNS['CT2'] = [('lump1', ["sensor1", "date", "time", "sensor2", "temperature"])]
EXPAND_COLUMNS['OOS'] = [('lump1', ["sensor1", "date", "time", "sensor2", "_1", "_2", "_3", "_4", "oxygen", "_5", "air_saturation", "_6", "temperature_c", "_7", "cal_phase", "_8", "tc_phase", "_9", "c1rph", "_10", "c2rph", "_11", "c1amp", "_12", "c2amp", "_13", "raw_temp_mv"])]
EXPAND_COLUMNS['CSV'] = []

KEEP_DF = {}
KEEP_DF["OBS"] = ["date", "time", "obs"]
KEEP_DF["CT2"] = ["date", "time", "temperature", "salinity", "conductivity", "pressure"]
KEEP_DF["OOS"] = ["date", "time", "oxygen"]
KEEP_DF['CSV'] = RAW_COLUMNS['CSV']

def load_from_file(path, format=None):
    """Accepts a pre-prepared format for data processing.
    
    format : {OBS, CT2, OOS, CSV}
    """
    extension = path.split('.')[-1]

    column_names = RAW_COLUMNS[extension]
    expand_columns = EXPAND_COLUMNS[extension]


    data = load_sensor_file(path, column_names, expand_columns)
    data = data[KEEP_DF[extension]]

    return data
    


def date_time_to_unix(date_str, time):
    reformatted_date = '-'.join(date_str.split('/'))
    d = datetime.date.fromisoformat(reformatted_date)
    # Converts to unix UTC time
    time_for_day = (d.toordinal() - datetime.date(1970, 1, 1).toordinal()) * 24*60*60
    

    time_piece = time.split(":")
    time_of_day = datetime.timedelta(
        hours = int(time_piece[0]),
        minutes = int(time_piece[1]),
        seconds = float(time_piece[2])
    )
    
    return time_for_day + time_of_day.total_seconds()
    

def get_row_by_value(data, column, value):
    index = bisect_left(data[column], value)
    return data.iloc[index]