from ffmpeg import probe
import utils

import scipy.linalg
import numpy as np
from collections import namedtuple
Image = namedtuple('Image', ['ru', 'rs', 'rv', 'gu', 'gs', 'gv', 'bu', 'bs', 'bv'])

def get_start_time(filename, unix=True):
    file_data = probe(filename)

    for stream in file_data['streams']:
        if 'timecode' in stream['tags']:
            timestamp = stream['tags']['timecode']
            day = stream['tags']['creation_time'].split('T')[0]
            if unix:
                return utils.date_time_to_unix(day, timestamp)
            return timestamp

    raise ValueError("No timestamp found")

def process_video(filename):
    """
    This function is designed to """
    pass


def compress_channel(channel, modes=50):
    U, S, V = scipy.linalg.svd(channel)
    return (U[:, :modes], S[:modes], V[:modes])
    
def compress_frame(frame):
    red_channel = frame[:, :, 0].reshape(len(frame), -1)
    green_channel = frame[:, :, 1].reshape(len(frame), -1)
    blue_channel = frame[:, :, 2].reshape(len(frame), -1)
    
    ru, rs, rv = compress_channel(red_channel)
    gu, gs, gv = compress_channel(green_channel)
    bu, bs, bv = compress_channel(blue_channel)
    
    return Image(ru, rs, rv, gu, gs, gv, bu, bs, bv)

def decompress_image(image):
    height = len(image.ru)
    width = len(image.rv[0, :])
    reconstruction = np.zeros((height, width, 3))
    reconstruction[:, :, 0] = image.ru@np.diag(image.rs)@image.rv
    reconstruction[:, :, 1] = image.gu@np.diag(image.gs)@image.gv
    reconstruction[:, :, 2] = image.bu@np.diag(image.bs)@image.bv
    return reconstruction.astype('uint8')

