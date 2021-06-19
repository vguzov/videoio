from setuptools import setup
version = '0.2.3'

with open("README.md", "r") as fi:
    long_description = fi.read()

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
    long_description_content_type='text/markdown',
    install_requires=["numpy", "ffmpeg-python"],
    classifiers=classifiers
)
