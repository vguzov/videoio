import os
import ffmpeg
import subprocess
from typing import Dict, Union
from pathlib import Path

H264_PRESETS = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'veryslow']


def read_video_params(path: Union[str, Path], stream_number: int = 0) -> Dict:
    """
    Read _resolution and frame rate of the video
    Args:
        path (str, Path): Path to input file
        stream_number (int): Stream number to extract video parameters from
    Returns:
        dict: Dictionary with height, width and FPS of the video
    """
    path = str(path)
    if not os.path.isfile(path):
        raise FileNotFoundError("{} does not exist".format(path))
    try:
        probe = ffmpeg.probe(path)
    except FileNotFoundError:
        raise FileNotFoundError("ffprobe not found, please reinstall ffmpeg")
    video_streams = [s for s in probe['streams'] if s['codec_type'] == 'video']
    stream_params = video_streams[stream_number]
    fps_splitted = [int(x) for x in stream_params['avg_frame_rate'].split('/')]
    fps = fps_splitted[0] if fps_splitted[1] == 1 else fps_splitted[0] / float(fps_splitted[1])
    width = stream_params['width']
    height = stream_params['height']
    if 'nb_frames' in stream_params:
        try:
            length = int(stream_params['nb_frames'])
        except ValueError:
            length = None
    else:
        length = None
    if ('tags' in stream_params) and ('rotate' in stream_params['tags']):
        rotation = int(stream_params['tags']['rotate'])
        if rotation % 90 == 0 and rotation % 180 != 0:
            width = stream_params['height']
            height = stream_params['width']
    params = {'width': width, 'height': height, 'fps': fps}
    if length is not None:
        params['length'] = length
    return params


def ensure_encoder_presence(codec="libx264"):
    try:
        p = subprocess.Popen(["ffprobe", "-encoders"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        encoders_list, err_stream = p.communicate()
    except FileNotFoundError:
        raise FileNotFoundError("ffprobe not found, please reinstall ffmpeg")

    if codec not in encoders_list.decode("utf-8"):
        err_message = f"Codec {codec} is not available in the installed ffmpeg version."
        if codec in ["libx264", "libx265"]:
            err_message += (f"Make sure ffmpeg is installed with --enable-{codec} \n"
                            f"HINT: For conda users, run `conda remove ffmpeg` and `conda install ffmpeg {codec[-4:]} -c conda-forge`")
        raise ValueError(err_message)
