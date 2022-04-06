import os
import ffmpeg
from typing import Dict


H264_PRESETS = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'veryslow']
LOSSLESS_CODECS = ["h264"]


def read_video_params(path: str, stream_number: int = 0) -> Dict:
    """
    Read resolution and frame rate of the video
    Args:
        path (str): Path to input file
        stream_number (int): Stream number to extract video parameters from
    Returns:
        dict: Dictionary with height, width and FPS of the video
    """
    if not os.path.isfile(path):
        raise FileNotFoundError("{} does not exist".format(path))
    probe = ffmpeg.probe(path)
    video_streams = [s for s in probe['streams'] if s['codec_type'] == 'video']
    stream_params = video_streams[stream_number]
    fps_splitted = [int(x) for x in stream_params['avg_frame_rate'].split('/')]
    fps = fps_splitted[0] if fps_splitted[1] == 1 else fps_splitted[0]/float(fps_splitted[1])
    width = stream_params['width']
    height = stream_params['height']
    if 'nb_frames' in stream_params:
        try:
            length = int(stream_params['nb_frames'])
        except ValueError:
            length = None
    else:
        length = None
    if 'rotate' in stream_params['tags']:
        rotation = int(stream_params['tags']['rotate'])
        if rotation%90==0 and rotation%180!=0:
            width = stream_params['height']
            height = stream_params['width']
    params = {'width': width, 'height': height, 'fps': fps}
    if length is not None:
        params['length'] = length
    return params
