# ROI Coordinate Selector Tool
Interactive tool for capturing polygon ROI coordinates from RTSP camera streams

## Role in Overall Pipeline
- Development/configuration tool, not part of runtime pipeline
- Used to determine ROI coordinates before camera configuration
- Output coordinates are manually copied into camera configuration JSON
- No dependencies on other modules (standalone utility)

## Location
```
sakshi/test/get_roi_coordinates.py
```

## Inputs
- RTSP URL (hardcoded in script, line 33)
- User mouse clicks on video window (interactive)
- Keyboard commands:
  - `c` - complete polygon
  - `r` - reset points
  - `s` - save and display coordinates
  - `q` - quit without saving

## Outputs
- Terminal output: List of `[x, y]` coordinates
- Format: `roi_points = [[x1, y1], [x2, y2], ...]`
- Visual feedback: Green polygon overlay on video stream
- No file output - coordinates must be manually copied

## Internal Logic
1. Connect to RTSP stream using OpenCV + FFmpeg backend
2. Set environment variable: `OPENCV_FFMPEG_CAPTURE_OPTIONS = 'rtsp_transport;tcp|max_delay;500000'`
3. Open VideoCapture with:
   - Backend: `cv2.CAP_FFMPEG`
   - Connection timeout: 10000ms
   - Read timeout: 10000ms
   - Buffer size: 1 (minimize latency)
4. Continuous frame reading loop
5. Mouse callback captures click coordinates
6. Visual overlay draws polygon edges and vertices
7. On `c` key: complete polygon with semi-transparent fill
8. On `s` key: print coordinates to terminal

## RTSP Connection Method
Identical to `camera/streams/opencv.py` start() method:
```python
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp|max_delay;500000'
cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG, [
    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000,
    cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000,
])
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
```

## Configuration Dependencies
None - fully standalone

## Known Constraints & Decisions
- TCP transport required (UDP causes "Operation not permitted" errors)
- FFmpeg backend required (OpenCV's CAP_FFMPEG flag)
- Timeout parameters mandatory for network-based cameras
- Buffer size = 1 to reduce latency
- RTSP URL format: `rtsp://user:pass@ip:port/path?channel=X&subtype=Y`
- Tested with: `rtsp://admin:admin@132.154.208.136:570/cam/realmonitor?channel=3&subtype=1`

## Usage Workflow
1. Edit script line 33 to set RTSP URL
2. Run: `python get_roi_coordinates.py`
3. Click polygon vertices on video
4. Press `c` to close polygon
5. Verify visual overlay
6. Press `s` to output coordinates
7. Copy coordinates from terminal
8. Paste into camera configuration API payload

## Technical Issues Resolved
- OpenCV CAP_FFMPEG warning: "backend is generally available but can't be used to capture by name"
  - Issue: Parameter syntax incompatibility
  - Solution: Pass timeout parameters as list, not kwargs
- RTSP connection failures with FFmpeg subprocess approach
  - Issue: Stream resolution auto-detection unreliable
  - Solution: Use OpenCV VideoCapture directly with proper backend flags
- "Operation not permitted" with TCP transport
  - Issue: Camera network restrictions
  - Solution: Environment variable `OPENCV_FFMPEG_CAPTURE_OPTIONS` with TCP transport

## Dependencies
- Python packages: `cv2`, `numpy`, `os`, `sys`
- System: FFmpeg (must be compiled into OpenCV)
- Network: Direct RTSP access to camera

## Drawing Behavior
- Green circles (5px radius) at each vertex
- Green lines connecting vertices
- Semi-transparent green fill (30% alpha) when polygon completed
- Real-time preview line from last point to cursor during drawing

## Global State
- `roi_points`: List of `[x, y]` coordinates
- `drawing`: Boolean flag for mouse movement tracking
- `frame`: Current video frame (global for mouse callback access)
- `img_copy`: Working copy for overlay drawing
