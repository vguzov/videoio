from setuptools import setup
version = '0.1.0'


long_description = """
videoio: save/load image sequence as H.264 video
A small library for saving and loading RGB and uint16 (depth) frames as H.264 encoded video.

Github: https://github.com/vguzov/videoio
"""

keywords = ["mp4", "png", "h264", "video", "image", "depth", "ffmpeg"]

classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3'
    ]

setup(
    name="videoio",
    packages=["videoio"],
    version=version,
    description="Module for saving and loading images and depth as H.264 video",
    author="Vladimir Guzov",
    author_email="guzov.mail@gmail.com",
    url="https://github.com/vguzov/videoio",
    keywords=keywords,
    long_description=long_description,
    install_requires=["numpy", "ffmpeg-python"],
    classifiers=classifiers
)
