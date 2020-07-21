import os
import numpy as np
import ffmpeg
from typing import Tuple
from .info import read_video_params, H264_PRESETS


def uint16read(path: str, output_resolution: Tuple[int, int] = None) -> np.ndarray:
    """
    Read 16-bit unsigned integer array encoded with uint16save function
    Args:
        path (str): Path to input file
        output_resolution (Tuple[int, int]): Sets the resolution of the result (width, height).
            If None, resolution will be the same as resolution of original video.
            Warning: changing this parameter may lead to undesirable data corruption.
    Returns:
        np.ndarray: 3-dimensional array of uint16 datatype
    """
    if not os.path.isfile(path):
        raise FileNotFoundError("{} does not exist".format(path))

    video_params = read_video_params(path, stream_number=0)
    resolution = (video_params['width'], video_params['height'])
    ffmpeg_input = ffmpeg.input(path, loglevel='error')
    if output_resolution is not None:
        resolution = output_resolution
        ffmpeg_input = ffmpeg_input.filter("scale", *resolution)
    ffmpeg_process = (
        ffmpeg_input
            .output('pipe:', format='rawvideo', pix_fmt='yuv444p')
            .global_args('-nostdin')
            .run_async(pipe_stdout=True)
    )
    frames = []
    while True:
        in_bytes = ffmpeg_process.stdout.read(np.prod(resolution) * 3)
        if not in_bytes:
            break
        in_frame = (
            np
                .frombuffer(in_bytes, np.uint8)
                .reshape(3, *resolution[::-1])
        )
        upper_part = in_frame[2,:,:]
        lower_coding = in_frame[0,:,:]
        upper_isodd = upper_part % 2 == 1
        lower_part = lower_coding.copy()
        lower_part[upper_isodd] = 255-lower_part[upper_isodd]
        frame = lower_part.astype(np.uint16) + upper_part.astype(np.uint16) * 256
        frames.append(frame)

    ffmpeg_process.wait()
    return np.array(frames)


def uint16save(path: str, data: np.ndarray, preset: str = 'slow', fps: float = None):
    """
    Store 3-dimensional uint16 array in H.264 encoded video
    Args:
        path (str): Path to output video
        data (np.ndarray): 3-dimentional uint16 NumPy array
        preset (str): H.264 compression preset
        fps (float): Target FPS. If None, will be set to ffmpeg's default
    """
    data = np.array(data)
    assert len(data[0].shape) == 2, "Multiple dimentions is not supported"
    assert data.dtype == np.uint16 or data.dtype == np.uint8, "Dtype {} is not supported".format(data.dtype)
    assert preset in H264_PRESETS, "Preset '{}' is not supported by libx264, supported presets are {}".\
        format(preset, H264_PRESETS)
    resolution = data[0].shape[::-1]
    input_params = dict(format='rawvideo', pix_fmt='yuv444p', s='{}x{}'.format(*resolution), loglevel='error')
    if fps is not None:
        input_params['framerate'] = fps
    ffmpeg_input = ffmpeg.input('pipe:', **input_params)
    encoding_params = {'c:v': 'libx264', 'preset': preset, 'profile:v': 'high444', 'crf': 0}
    ffmpeg_process = (
        ffmpeg_input
            .output(path, pix_fmt='yuv444p', **encoding_params)
            .overwrite_output()
            .run_async(pipe_stdin=True)
    )
    zeros = np.zeros(data.shape, dtype=np.uint8)
    if data.dtype == np.uint16:
        upper_part = (data/256).astype(np.uint8)
        lower_part = (data%256).astype(np.uint8)
        upper_isodd = upper_part%2 == 1
        lower_coding = lower_part.copy()
        lower_coding[upper_isodd] = 255-lower_coding[upper_isodd]
        # lower_coding = lower_coding.astype(np.uint8)
        data = np.stack([lower_coding, zeros, upper_part], axis=1)
        # data = np.stack([(data%256).astype(np.uint8), (data/256).astype(np.uint8), zeros], axis=1)
    else:
        data = np.stack([data, zeros, zeros], axis=1)
    for frame in data:
        ffmpeg_process.stdin.write(frame.tobytes())
    ffmpeg_process.stdin.close()
    ffmpeg_process.wait()

class Uint16Reader:
    def __init__(self, path: str, output_resolution: Tuple[int, int] = None):
        """
        Iterable class for reading uint16 data sequentially
        Args:
            path (str): Path to input file
            output_resolution (Tuple[int, int]): Sets the resolution of the result (width, height).
                If None, resolution will be the same as resolution of original video.
                Warning: changing this parameter may lead to undesirable data corruption.
        """
        self.path = path
        if not os.path.isfile(path):
            raise FileNotFoundError("{} does not exist".format(path))

        self.video_params = read_video_params(path, stream_number=0)
        self.resolution = np.array((self.video_params['width'], self.video_params['height']))
        if output_resolution is not None:
            self.resolution = output_resolution
            self.apply_scale = True
        else:
            self.apply_scale = False

    def __iter__(self):
        ffmpeg_input = ffmpeg.input(self.path, loglevel='error')
        if self.apply_scale:
            ffmpeg_input = ffmpeg_input.filter("scale", *self.resolution)
        self.ffmpeg_process = (
            ffmpeg_input
            .output('pipe:', format='rawvideo', pix_fmt='yuv444p')
            .global_args('-nostdin')
            .run_async(pipe_stdout=True)
        )
        return self

    def __next__(self) -> np.ndarray:
        in_bytes = self.ffmpeg_process.stdout.read(np.prod(self.resolution) * 3)
        if not in_bytes:
            raise StopIteration
        in_frame = np.frombuffer(in_bytes, np.uint8).reshape(3, *self.resolution[::-1])
        upper_part = in_frame[2, :, :]
        lower_coding = in_frame[0, :, :]
        upper_isodd = upper_part % 2 == 1
        lower_part = lower_coding.copy()
        lower_part[upper_isodd] = 255 - lower_part[upper_isodd]
        frame = lower_part.astype(np.uint16) + upper_part.astype(np.uint16) * 256
        return frame

class Uint16Writer:
    """
    Class for storing a sequence of uint16 arrays in H.264 encoded video
    """
    def __init__(self, path: str, resolution: Tuple[int, int], preset: str = 'slow', fps: float = None):
        """
        Args:
            path (str): Path to output video
            resolution (Tuple[int, int]): Resolution of the input frames and output video (width, height)
            preset (str): H.264 compression preset
            fps (float): Target FPS. If None, will be set to ffmpeg's default
        """
        assert preset in H264_PRESETS, "Preset '{}' is not supported by libx264, supported presets are {}".\
            format(preset, H264_PRESETS)
        input_params = dict(format='rawvideo', pix_fmt='yuv444p', s='{}x{}'.format(*resolution), loglevel='error')
        if fps is not None:
            input_params['framerate'] = fps
        ffmpeg_input = ffmpeg.input('pipe:', **input_params)
        encoding_params = {'c:v': 'libx264', 'preset': preset, 'profile:v': 'high444', 'crf': 0}
        self.ffmpeg_process = (
            ffmpeg_input
                .output(path, pix_fmt='yuv444p', **encoding_params)
                .overwrite_output()
                .run_async(pipe_stdin=True)
        )

    def write(self, data: np.ndarray):
        """
        Write next portion of data
        Args:
            data (np.ndarray): data to write
        """
        assert len(data.shape) == 2, "Multiple dimensions is not supported"
        assert data.dtype == np.uint16 or data.dtype == np.uint8, "Dtype {} is not supported".format(data.dtype)
        zeros = np.zeros(data.shape, dtype=np.uint8)
        if data.dtype == np.uint16:
            upper_part = (data / 256).astype(np.uint8)
            lower_part = (data % 256).astype(np.uint8)
            upper_isodd = upper_part % 2 == 1
            lower_coding = lower_part.copy()
            lower_coding[upper_isodd] = 255 - lower_coding[upper_isodd]
            data = np.stack([lower_coding, zeros, upper_part], axis=0)
        else:
            data = np.stack([data, zeros, zeros], axis=0)
        self.ffmpeg_process.stdin.write(data.tobytes())

    def close(self):
        """
        Finish video creation process and close video file
        """
        self.ffmpeg_process.stdin.close()
        self.ffmpeg_process.wait()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()