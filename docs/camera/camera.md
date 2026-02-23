# Camera Management Module
RTSP stream connection, frame capture, and ROI masking for object detection pipeline

## Role in Overall Pipeline
- Connects to RTSP cameras and maintains persistent stream connections
- Extracts frames at configured FPS (1-30)
- Applies ROI polygon masks to frames
- Provides frame data to Detection API
- Manages camera lifecycle (start/stop/health)

Dependencies (upstream):
- None (entry point module)

Dependencies (downstream):
- Detection module calls `camera_manager.get_camera_stream()` for frame access
- Common module for utilities (`common.utils`, `common.config`, `common.logger`)

## Inputs

### API Endpoints

#### POST /camera/start
Single camera mode (< 10 cameras)

```json
{
  "rtsp_url": "rtsp://admin:admin@192.168.1.100:554/cam/realmonitor?channel=1&subtype=1",
  "camera_id": "cam_1",
  "fps": 5,
  "roi_points": [[1055.55, 536.47], [951.55, 452.47], [1101.55, 347.47], [1228.55, 413.47]]
}
```

Schema: `RTSPConfig` (camera/schemas.py)
- `rtsp_url`: string (required)
- `camera_id`: string (required, unique identifier)
- `fps`: int (1-30, default: 5)
- `roi_points`: List[List[float]] (optional, polygon vertices in image coordinates)

#### POST /camera/start-multi
Multi-stream batch mode (100+ cameras, requires NVIDIA DeepStream pyds module)

```json
{
  "batch_size": 30,
  "width": 1920,
  "height": 1080,
  "streams": [
    {
      "rtsp_url": "rtsp://admin:admin@192.168.1.100:554/cam/realmonitor?channel=1&subtype=1",
      "camera_id": "cam_1",
      "fps": 5,
      "roi_points": [[1055.55, 536.47], [951.55, 452.47], [1101.55, 347.47], [1228.55, 413.47]]
    }
  ]
}
```

Schema: `MultiStreamConfig` (camera/schemas.py)
- `streams`: List[RTSPConfig] (required, min 1 camera)
- `batch_size`: int (1-128, default: 30)
- `width`: int (≥640, default: 1920)
- `height`: int (≥480, default: 1080)

#### GET /camera/status/{camera_id}
Returns `CameraStatus` schema

#### GET /camera/frame/{camera_id}
Query params: `include_metadata` (bool, default: true)

Returns frame as base64-encoded JPEG + metadata

#### GET /camera/list
No params

#### DELETE /camera/stop/{camera_id}
Single camera only

#### DELETE /camera/stop-multi
Stops entire multi-stream pipeline

#### DELETE /camera/stop-all
Emergency stop (all modes)

#### GET /camera/health
Service health check

## Outputs

### Response Schemas

#### CameraStatus
```json
{
  "camera_id": "cam_1",
  "is_running": true,
  "backend": "opencv-ffmpeg",
  "fps": 5,
  "frame_count": 128,
  "last_frame_time": 1770967225.896413,
  "rtsp_url": "rtsp://admin:admin@..."
}
```

#### Frame Response (single-stream)
```json
{
  "camera_id": "cam_1",
  "frame": "base64_encoded_jpeg_data",
  "status": "frame_ready",
  "backend": "opencv-ffmpeg",
  "timestamp": 1770967225.896413,
  "shape": [1080, 1920, 3],
  "roi_points": [[1055.55, 536.47], ...],
  "frame_count": 128,
  "has_roi_mask": true
}
```

### Internal Data Structures (for Detection API)

`camera_manager.get_camera_stream(camera_id)` returns OpenCVCamera instance

`camera.get_preprocessed_frame()` returns:
```python
{
  'frame': np.ndarray,        # BGR image (H, W, 3)
  'timestamp': float,         # Unix timestamp
  'shape': tuple,             # (H, W, C)
  'roi_points': List[List],   # Original polygon vertices
  'roi_mask': np.ndarray,     # Binary mask (255=ROI, 0=outside)
  'frame_count': int          # Total frames captured
}
```

## Internal Logic

### Single Camera Flow (OpenCVCamera)

1. **Initialization** (`__init__`)
   - Store camera_id, rtsp_url, fps, roi_points
   - Create `cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)`
   - Initialize threading.Lock() for frame access
   - Set running=False, frame=None

2. **Start** (`start()`)
   - Open RTSP stream with `cap.open(rtsp_url)`
   - Read first frame to verify connection (timeout if fails)
   - Spawn daemon thread running `_capture_loop()`
   - Set running=True

3. **Capture Loop** (`_capture_loop()`)
   - Runs in background thread until stopped
   - Rate-limited to 1/fps seconds per iteration
   - Read frame: `ret, frame = cap.read()`
   - If read fails: increment error_count (max 10 consecutive failures)
   - On success:
     - Acquire frame_lock
     - Update self.current_frame, self.frame_count, self.last_frame_time
     - Release frame_lock
     - Reset error_count=0
   - On first successful frame: call `_create_roi_mask()` if roi_points exist
   - Loop uses `asyncio.sleep()` for non-blocking delays

4. **ROI Mask Creation** (`_create_roi_mask()`)
   - Called once on first frame
   - Convert roi_points to np.int32 array
   - Create black image same size as frame
   - `cv2.fillPoly(mask, [polygon], 255)` to fill ROI region
   - Store as self.roi_mask (single-channel, uint8)

5. **Frame Retrieval** (`get_preprocessed_frame()`)
   - Acquire frame_lock
   - Return dict with frame + metadata
   - Release frame_lock
   - Returns None if no frame available yet

6. **Stop** (`stop()`)
   - Set running=False (stops capture loop)
   - Join thread (wait for loop to exit)
   - Release cv2.VideoCapture
   - Clear frame data

### Multi-Stream Flow (MultiStreamManager)

**Status:** Not operational (requires NVIDIA DeepStream SDK + pyds Python bindings)

Architecture:
- GStreamer pipeline with batched sources
- `uridecodebin` for RTSP → `nvstreammux` for batching → `appsink` for frame extraction
- Processes multiple cameras in GPU-optimized batches
- Each camera gets stream_index in batch

Not documented in detail (not currently functional)

### Camera Manager (CameraManager)

Central coordinator singleton: `camera_manager` instance

State:
- `single_cameras: Dict[str, OpenCVCamera]` - active single-mode cameras
- `multi_stream_manager: Optional[MultiStreamManager]` - batch mode instance
- `pipeline_workers: Dict[str, Thread]` - background processing threads
- `pipeline_stop_events: Dict[str, Event]` - graceful shutdown signals

Rules:
- Cannot mix single and multi-stream modes simultaneously
- Multi-stream mode: cannot stop individual cameras (must stop entire batch)
- Single-stream mode: each camera independent lifecycle

Methods:
- `start_single_camera(config)` → creates OpenCVCamera, starts it
- `start_multi_stream(streams, batch, w, h)` → creates MultiStreamManager (fails if pyds unavailable)
- `stop_camera(camera_id)` → stops single camera
- `stop_multi_stream()` → stops batch pipeline
- `stop_all()` → emergency shutdown
- `get_camera_stream(camera_id)` → returns camera instance for detection
- `get_camera_status(camera_id)` → returns CameraStatus
- `list_cameras()` → inventory of active cameras

## Database Interaction
None. Stateless in-memory management only.

## Configuration Dependencies

From `common/config.py`:
- `DEFAULT_FPS = 5`
- `MAX_FPS = 30`
- `MIN_FPS = 1`
- `MAX_CAMERAS_SINGLE_MODE = 50`
- `DEFAULT_CAMERA_TIMEOUT = 30` (seconds)
- `MULTI_STREAM_BATCH_SIZE = 4`
- `MULTI_STREAM_WIDTH = 1280`
- `MULTI_STREAM_HEIGHT = 720`

No runtime environment variables currently used.

## Threading / Lifecycle Behavior

### Single Camera Threading

Each OpenCVCamera spawns **1 daemon thread** in `start()`:
- Thread runs `_capture_loop()` continuously
- Rate-limited to capture_interval = 1/fps seconds
- Uses `threading.Lock()` for thread-safe frame access
- Daemon mode: thread auto-terminates if main process dies
- Graceful stop: set `running=False`, thread exits loop, joins within 2s timeout

Thread lifecycle:
```
start() → spawn daemon thread → _capture_loop() runs indefinitely
                                      ↓
                         loop checks self.running every iteration
                                      ↓
stop() sets running=False → loop exits → thread terminates → join()
```

### Multi-Stream Threading

Not currently active (pyds unavailable). Would use:
- GStreamer main loop in separate thread
- Callbacks on frame availability
- Batched processing across cameras

### Cleanup Rules

On application shutdown (main.py lifespan):
1. `await camera_manager.stop_all()` called
2. Stops all single cameras (each joins its thread)
3. Stops multi-stream pipeline if active
4. Releases all cv2.VideoCapture resources

On individual camera stop:
1. Set running=False
2. Wait for thread to exit (join with 2s timeout)
3. Release VideoCapture handle
4. Remove from camera_manager.single_cameras dict

## Known Constraints & Decisions

### Backend Selection

**OpenCV + FFmpeg (current production):**
- Used for single-camera mode
- Compatible with Dahua cameras (user's RTSP source)
- Uses `cv2.CAP_FFMPEG` backend explicitly
- Tested working with `rtsp://admin:admin@132.154.208.136:570/cam/realmonitor?channel=1&subtype=1`

**GStreamer + DeepStream (not operational):**
- Code exists in `camera/streams/deepstream.py` and `camera/streams/multi_stream.py`
- Requires NVIDIA GPU + DeepStream SDK 6.4 + pyds Python bindings
- Failed with Dahua cameras (ERROR 250 during RTSP PLAY command)
- Pipeline: `rtspsrc → rtph264depay → h264parse → nvv4l2decoder → videoconvert → appsink`
- Multi-stream mode disabled when `PYDS_AVAILABLE = False`

**Why OpenCV chosen:**
- Same underlying codec support as VLC (FFmpeg)
- No GPU dependencies for small camera counts
- Direct compatibility with user's existing hardware
- Simpler deployment (no Docker/DeepStream setup)

### ROI Implementation

**Design decision:** ROI stored as polygon points, converted to binary mask on first frame
- Mask created once (not per-frame) for performance
- Stored as uint8 numpy array (255=inside, 0=outside)
- Applied by detection module, not camera module (separation of concerns)
- Camera only provides roi_mask to detection API

### Frame Rate Control

**Rate limiting in capture loop:**
```python
await asyncio.sleep(1.0 / self.fps)
```
- Not precise frame timing (subject to processing delays)
- Acceptable for 5 FPS use case (queue monitoring)
- For higher precision, would need timestamp-based scheduling

### Error Handling

**RTSP stream failures:**
- Max 10 consecutive read failures before stopping camera
- Each failure logged with warning
- No automatic reconnection (manual restart required via API)

**Missing frames:**
- `get_preprocessed_frame()` returns None if no frame captured yet
- Detection API must handle 503 response during camera initialization

## How This Module Scales

### Single-Camera Mode Scaling

**Tested:** 1 camera at 1080p @ 5 FPS ✓  
**Theoretical limit:** ~50 cameras (configurable in `MAX_CAMERAS_SINGLE_MODE`)

Each camera:
- 1 thread (minimal CPU overhead)
- ~3-5% CPU per camera (OpenCV decoding)
- Memory: ~10-20 MB per camera (frame buffer)

Bottlenecks:
- Network bandwidth (1080p @ 5 FPS ≈ 2-3 Mbps per camera)
- CPU decoding (no GPU acceleration in single mode)
- Thread count (OS limit ~1000-10000 threads)

**Do NOT change:** Frame locking mechanism (required for thread safety)

### Multi-Camera Behavior

**Current state:** Each camera fully independent
- No shared resources between cameras
- No batch processing
- No GPU utilization

**If enabling multi-stream mode:**
- Cameras processed in batches (default 30)
- Single GStreamer pipeline for all cameras
- GPU-accelerated decoding (NVDEC)
- Requires stopping ALL cameras to add/remove one (batch limitation)

### Multi-Usecase Behavior

Camera module is **usecase-agnostic:**
- Same camera can serve multiple detection requests
- Frame buffer shared (last captured frame)
- No per-usecase frame storage
- Detection module handles usecase routing

**Do NOT change:** Frame storage strategy (last-frame-only)
- Changing to buffered frames would increase memory ~100x
- Current design assumes real-time processing only

### What Should NOT Be Changed Lightly

1. **Threading model:** Daemon threads critical for graceful shutdown
2. **Frame locking:** Race conditions if removed
3. **CAP_FFMPEG backend:** GStreamer incompatible with Dahua cameras
4. **Single-mode independence:** Required for partial failures (one camera down ≠ all cameras down)
5. **ROI mask creation timing:** Must happen after first frame (need image dimensions)

### Safe to Modify

- FPS limits (MIN_FPS, MAX_FPS)
- Error tolerance (max_errors=10)
- JPEG encoding quality (currently 85)
- Camera timeout (DEFAULT_CAMERA_TIMEOUT)
- Batch size for multi-stream (if enabling DeepStream)

## File Structure

```
camera/
├── __init__.py              # Module exports
├── api.py                   # FastAPI router (11 endpoints)
├── service.py               # CameraManager singleton
├── schemas.py               # Pydantic models (RTSPConfig, MultiStreamConfig, CameraStatus)
└── streams/
    ├── __init__.py          # Stream backend exports
    ├── opencv.py            # OpenCVCamera (PRODUCTION)
    ├── deepstream.py        # DeepStreamCamera (UNUSED - GStreamer incompatible)
    └── multi_stream.py      # MultiStreamManager (DISABLED - requires pyds)
```

Integration points:
- `main.py` includes router: `app.include_router(camera_router)`
- `detection/api.py` calls: `camera_manager.get_camera_stream(camera_id)`
- `common/utils.py` provides: `validate_rtsp_url()`, `create_roi_mask()`, `apply_roi_to_frame()`

## Flow Tracking

All functions log completion with "✓" marker for debugging:
```python
logger.info(f"✓ start_camera completed for {camera_id}")
```

Log file: `camera_api.log` (configured in `main.py`)

Verify camera operation:
```bash
tail -f camera_api.log | grep "✓"
```

Expected log sequence for camera start:
1. `✓ validate_rtsp_url completed: True`
2. `✓ OpenCVCamera.start completed`
3. `✓ CameraManager.start_single_camera completed for {camera_id}`
4. `✓ start_camera completed for {camera_id}`
5. `✓ OpenCVCamera._create_roi_mask completed` (if ROI provided)

## Testing Commands

Start camera:
```bash
curl -X POST http://localhost:8000/camera/start \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "test_cam",
    "rtsp_url": "rtsp://admin:admin@132.154.208.136:570/cam/realmonitor?channel=1&subtype=1",
    "fps": 5,
    "roi_points": [[1055.55, 536.47], [951.55, 452.47], [1101.55, 347.47], [1228.55, 413.47]]
  }'
```

Check status:
```bash
curl http://localhost:8000/camera/status/test_cam
```

Get frame:
```bash
curl http://localhost:8000/camera/frame/test_cam | jq .
```

List cameras:
```bash
curl http://localhost:8000/camera/list
```

Stop camera:
```bash
curl -X DELETE http://localhost:8000/camera/stop/test_cam
```

Health check:
```bash
curl http://localhost:8000/camera/health
```
