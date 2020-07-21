# videoio: save/load image sequence as H.264 video
A small library for saving and loading RGB and uint16 (depth) frames as H.264 encoded video

## Quickstart
##### Save/load RGB frames:
```python
import numpy as np
from videoio import videosave, videoread
frames = np.random.random((20,200,400,3)) #[framesNr, height, width, RGB]
# Save to video
videosave("out.mp4", frames)
# Load from video
frames = videoread("out.mp4")
```

##### Read frames sequentially:
```python
from videoio import VideoReader
for frame in VideoReader("in.mp4"):
    do_something_with(frame)
```

##### Write frames sequentially:
```python
from videoio import VideoWriter
writer = VideoWriter("out.mp4", resolution=(400, 200)) #[width, height]
for i in range(100):
    frame = get_frame()
    writer.write(frame)
writer.close()
```
or
```python
with VideoWriter("out.mp4", resolution=(400, 200)) as writer:
    for i in range(100):
        frame = get_frame()
        writer.write(frame)
```

##### Lossless write/read of uint16 3D arrays (useful for saving depth frames stored in mm, for example Kinect data):
```python
import numpy as np
from videoio import uint16save, uint16read
# Generate 20 random depth frames
depth_frames = (np.random.random((20,200,400))*65535).astype(np.uint16)
# Save
uint16save("out_depth.mp4", depth_frames)
# Load
depth_frames = uint16read("out_depth.mp4")
```

##### Save RGB frames in lossless mode with different compression preset and different FPS:
```python
videosave("out.mp4", frames, lossless=True, preset="veryfast", fps=10.5)
```

##### Read RGB frames and scale them to target resolution simultaneously:
```python
frames = videoread("in.mp4", output_resolution=(100, 250))
```

## Prerequisites
- ffmpeg with libx264 enabled and ffprobe (usually comes with ffmpeg)
- NumPy
- ffmpeg-python

## Installation
From pip:
```
pip install videoio
```

From source:
```
git clone https://github.com/vguzov/videoio.git
python setup.py install
```