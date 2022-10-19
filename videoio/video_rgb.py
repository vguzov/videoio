import os
import numpy as np
import ffmpeg
import warnings
from pathlib import Path
from typing import Tuple, Dict, Union, Optional
from .info import read_video_params, H264_PRESETS


def videoread(path: Union[str, Path], return_attributes: bool = False, stream_number: int = 0,
        output_resolution: Tuple[int, int] = None, output_fps: float = None, start_frame: int = 0,
        respect_original_timestamps: bool = False) \
        -> Union[np.ndarray, Tuple[np.ndarray, Dict]]:
    """
    Reads an input video to a NumPy array
    Args:
        path (str, Path): Path to input file
        return_attributes (bool): Whether to return a dictionary with original video _resolution and frame rate
        stream_number (int): Stream number to extract video parameters from
        output_resolution (Tuple[int, int]): Sets the _resolution of the result (width, height).
            If None, _resolution will be the same as _resolution of original video.
        output_fps (float): Sets the output framerate of the video to the given value.
            Useful to work with VFR (Variable Frame Rate) videos. If None, will keep the original framerate (whether variable or constant).
        start_frame (int): frame to start reading from.
            Correct behaviour is guaranteed only if input video was produced by videoio.
            If output_fps is set, the timing is calculated according to the output_fps, otherwise average framerate of the original video is used.
        respect_original_timestamps (bool): whether to read frames according to timestamps or not
            If True, frames will be extracted according to framerate and video timestamps,
            otherwise just a raw stream of frames will be read

    Returns:
        np.ndarray: (if return_attributes == False) Frames of the video
        tuple: (if return_attributes == True) Tuple containing:
            np.ndarray: Frames of the video
            dict: Parameter of the video (original height and width and frame rate)
    """
    path = str(path)
    assert start_frame >= 0, "Starting frame should be positive"
    if not os.path.isfile(path):
        raise FileNotFoundError("{} does not exist".format(path))

    video_params = read_video_params(path, stream_number=stream_number)
    resolution = np.array((video_params['width'], video_params['height']))
    if start_frame != 0:
        if output_fps is None:
            start_frame_time = (start_frame - 0.5) / video_params['fps']
        else:
            start_frame_time = (start_frame - 0.5) / output_fps
        ffmpeg_input = ffmpeg.input(path, loglevel='error', ss=start_frame_time)
    else:
        ffmpeg_input = ffmpeg.input(path, loglevel='error')
    if output_resolution is not None:
        resolution = output_resolution
        ffmpeg_input = ffmpeg_input.filter("scale", *resolution)
    if output_fps is not None:
        ffmpeg_input = ffmpeg_input.filter("fps", output_fps)
        respect_original_timestamps = True
    images = []
    if respect_original_timestamps:
        ffmpeg_output = ffmpeg_input.output('pipe:', format='rawvideo', pix_fmt='rgb24')
    else:
        ffmpeg_output = ffmpeg_input.output('pipe:', format='rawvideo', pix_fmt='rgb24', vsync='0')
    ffmpeg_process = ffmpeg_output.global_args('-nostdin').run_async(pipe_stdout=True)
    try:
        while True:
            in_bytes = ffmpeg_process.stdout.read(np.prod(resolution) * 3)
            if not in_bytes:
                break
            in_frame = np.frombuffer(in_bytes, np.uint8).reshape(*resolution[::-1], 3)
            images.append(in_frame)
    finally:
        ffmpeg_process.stdout.close()
        ffmpeg_process.wait()
    images = np.stack(images, axis=0)
    if return_attributes:
        return images, video_params
    return images


def videosave(path: Union[str, Path], images: np.ndarray, lossless: bool = False, preset: str = 'slow', fps: float = None):
    """
    Saves the video with encoded with H.264 codec
    Args:
        path (str, Path): Path to output video
        images (np.ndarray): NumPy array of video frames
        lossless (bool): Whether to apply lossless encoding.
            Be aware: lossless format is still lossy due to RGB to YUV conversion inaccuracy
        preset (str): H.264 compression preset
        fps (float): Target FPS. If None, will be set to ffmpeg's default
    """
    path = str(path)
    assert images[0].shape[2] == 3, "Alpha channel is not supported"
    assert preset in H264_PRESETS, "Preset '{}' is not supported by libx264, supported presets are {}". \
        format(preset, H264_PRESETS)
    resolution = images[0].shape[:2][::-1]
    input_params = dict(format='rawvideo', pix_fmt='rgb24', s='{}x{}'.format(*resolution), loglevel='error')
    if fps is not None:
        input_params['framerate'] = fps
    ffmpeg_input = ffmpeg.input('pipe:', **input_params)
    encoding_params = {"c:v": "libx264", "preset": preset}
    if lossless:
        encoding_params['profile:v'] = 'high444'
        encoding_params['crf'] = 0

    ffmpeg_process = ffmpeg_input.output(path, pix_fmt='yuv444p' if lossless else 'yuv420p', **encoding_params)

    ffmpeg_process = ffmpeg_process.overwrite_output().run_async(pipe_stdin=True)
    try:
        for color_frame in images:
            if color_frame.dtype == np.float16 or color_frame.dtype == np.float32 or color_frame.dtype == np.float64:
                color_frame = (color_frame * 255).astype(np.uint8)
            elif color_frame.dtype != np.uint8:
                raise NotImplementedError("Dtype {} is not supported".format(color_frame.dtype))
            ffmpeg_process.stdin.write(color_frame.tobytes())
    finally:
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()


class VideoReader:
    """
    Iterable class for reading video frame-by-frame
    """

    def __init__(self, path: Union[str, Path], stream_number: int = 0,
            output_resolution: Tuple[int, int] = None, output_fps: float = None, start_frame: int = 0,
            respect_original_timestamps: bool = False):
        """
        Args:
            path (str, Path): Path to input video
            stream_number (int): Stream number to extract video parameters from
            output_resolution (Tuple[int, int]): Sets the _resolution of the result (width, height).
                If None, _resolution will be the same as _resolution of original video.
            output_fps (float): Sets the output framerate of the video to the given value.
                Useful to work with VFR (Variable Frame Rate) videos. If None, will keep the original framerate (whether variable or constant).
            start_frame (int): frame to start reading from.
                Correct behaviour is guaranteed only if input video was produced by videoio.
                If output_fps is set, the timing is calculated according to the output_fps, otherwise average framerate of the original video is used.
            respect_original_timestamps (bool): whether to read frames according to timestamps or not
                If True, frames will be extracted according to framerate and video timestamps,
                otherwise just a raw stream of frames will be read
        """
        path = str(path)
        assert start_frame >= 0, "Starting frame should be positive"
        self.path = path
        self.start_frame = start_frame
        self.respect_original_timestamps = respect_original_timestamps
        self.output_fps = output_fps
        if not os.path.isfile(path):
            raise FileNotFoundError("{} does not exist".format(path))

        self.video_params = read_video_params(path, stream_number=stream_number)
        self._resolution = np.array((self.video_params['width'], self.video_params['height']))
        if output_resolution is not None:
            self._resolution = output_resolution
            self.apply_scale = True
        else:
            self.apply_scale = False
        if self.output_fps is not None:
            self.respect_original_timestamps = True
        self.ffmpeg_process = None

    def __iter__(self):
        if self.start_frame != 0:
            if self.output_fps is None:
                start_frame_time = (self.start_frame - 0.5) / self.video_params['fps']
            else:
                start_frame_time = (self.start_frame - 0.5) / self.output_fps
            ffmpeg_input = ffmpeg.input(self.path, loglevel='error', ss=start_frame_time)
        else:
            ffmpeg_input = ffmpeg.input(self.path, loglevel='error')
        if self.apply_scale:
            ffmpeg_input = ffmpeg_input.filter("scale", *self._resolution)
        if self.output_fps is not None:
            ffmpeg_input = ffmpeg_input.filter("fps", self.output_fps)
        if self.respect_original_timestamps:
            ffmpeg_output = ffmpeg_input.output('pipe:', format='rawvideo', pix_fmt='rgb24')
        else:
            ffmpeg_output = ffmpeg_input.output('pipe:', format='rawvideo', pix_fmt='rgb24', vsync='0')
        self.ffmpeg_process = ffmpeg_output.global_args('-nostdin').run_async(pipe_stdout=True)
        return self

    def __len__(self) -> int:
        if 'length' in self.video_params:
            return max(self.video_params['length'] - self.start_frame, 0)
        else:
            return 0

    @property
    def resolution(self) -> Tuple[int, int]:
        """
        Output frame resolution
        Returns:
            Tuple[int, int]: resolution in pixels
        """
        return self._resolution

    @property
    def fps(self) -> Optional[float]:
        """
        Output framerate, 1/time difference between frames (average time for VFR videos)
        Returns:
            float: framerate (1/sec) or None if no framerate info is found
        """
        if self.output_fps is not None:
            return self.output_fps
        else:
            if 'fps' in self.video_params:
                return self.video_params['fps']
            else:
                return None

    def close(self):
        """
        Close reader thread
        """
        if hasattr(self, "ffmpeg_process") and self.ffmpeg_process is not None:
            self.ffmpeg_process.stdout.close()
            self.ffmpeg_process.wait()

    def __next__(self) -> np.ndarray:
        in_bytes = self.ffmpeg_process.stdout.read(np.prod(self._resolution) * 3)
        if not in_bytes:
            raise StopIteration
        in_frame = np.frombuffer(in_bytes, np.uint8).reshape(*self._resolution[::-1], 3)
        return in_frame

    def __del__(self):
        self.close()


class VideoWriter:
    """
    Class for writing a video frame-by-frame
    """

    def __init__(self, path: Union[str, Path], resolution: Tuple[int, int], lossless: bool = False,
            preset: str = 'slow', fps: float = None):
        """
        Args:
            path (str, Path): Path to output video
            resolution (Tuple[int, int]): Resolution of the input frames and output video (width, height)
            lossless (bool): Whether to apply lossless encoding.
                Be aware: lossless format is still lossy due to RGB to YUV conversion inaccuracy
            preset (str): H.264 compression preset
            fps (float): Target FPS. If None, will be set to ffmpeg's default
        """
        path = str(path)
        assert preset in H264_PRESETS, "Preset '{}' is not supported by libx264, supported presets are {}". \
            format(preset, H264_PRESETS)
        self.resolution = resolution
        input_params = dict(format='rawvideo', pix_fmt='rgb24', s='{}x{}'.format(*resolution), loglevel='error')
        if fps is not None:
            input_params['framerate'] = fps
        ffmpeg_input = ffmpeg.input('pipe:', **input_params)
        encoding_params = {"c:v": "libx264", "preset": preset}
        if lossless:
            encoding_params['profile:v'] = 'high444'
            encoding_params['crf'] = 0

        ffmpeg_process = ffmpeg_input.output(path, pix_fmt='yuv444p' if lossless else 'yuv420p', **encoding_params)

        self.ffmpeg_process = ffmpeg_process.overwrite_output().run_async(pipe_stdin=True)

    def write(self, color_frame: np.ndarray):
        """
        Write next frame
        Args:
            color_frame (np.ndarray): RGB frame to write
        """
        assert color_frame.shape[2] == 3, "Alpha channel is not supported"
        assert all([self.resolution[i] == color_frame.shape[1 - i] for i in range(2)]), \
            "Resolution of color frame does not match with video _resolution – expected {}, got {}". \
                format(self.resolution, color_frame.shape[:2][::-1])
        if color_frame.dtype == np.float16 or color_frame.dtype == np.float32 or color_frame.dtype == np.float64:
            color_frame = (color_frame * 255).astype(np.uint8)
        elif color_frame.dtype != np.uint8:
            raise NotImplementedError("Dtype {} is not supported".format(color_frame.dtype))
        self.ffmpeg_process.stdin.write(color_frame.tobytes())

    def close(self):
        """
        Finish video creation process and close video file
        """
        if hasattr(self, "ffmpeg_process"):
            self.ffmpeg_process.stdin.close()
            self.ffmpeg_process.wait()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()
