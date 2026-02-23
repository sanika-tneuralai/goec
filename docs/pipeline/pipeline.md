# Pipeline Orchestration

Coordinates Camera → Detection → Usecase → Alert flow. Runs continuously per camera or on-demand via API.

## Role in Overall Pipeline

- Executes complete detection workflow from frame capture to alert delivery
- Two modes: on-demand (via HTTP endpoint) and continuous (background worker)
- No API depends on this module directly; this module calls all other APIs
- Entry point for end-to-end camera monitoring workflow

## Inputs

### On-Demand Mode (HTTP Endpoint)
**Endpoint:** `POST /pipeline/execute`

**Request Body:**
```json
{
  "camera_id": "s1_cam_1",
  "confidence_threshold": 0.5,
  "usecases": ["person_in_roi", "crowd_in_roi"]
}
```

**Fields:**
- `camera_id` (required): Camera identifier
- `confidence_threshold` (optional, default 0.5): Detection threshold 0.0-1.0
- `usecases` (optional): List of usecase IDs; defaults to all three

### Continuous Mode (Background Worker)
- Auto-starts when camera starts via `CameraManager.start_single_camera()`
- No external input; uses same camera_id and default parameters

## Outputs

### HTTP Response (On-Demand Mode)
```json
{
  "status": "success",
  "camera_id": "s1_cam_1",
  "pipeline_results": {
    "camera": {
      "status": "frame_ready",
      "backend": "opencv-ffmpeg"
    },
    "detection": {
      "total_detections": 5,
      "roi_detections": 2,
      "processing_time_ms": 45.3
    },
    "usecases": {
      "evaluated": 3,
      "triggered": 1,
      "results": [...]
    },
    "alerts": {
      "sent": 1,
      "details": [...]
    }
  }
}
```

### Side Effects (Both Modes)
- Triggers alert service (prints to console)
- Writes to `analytics.db` via usecase persistence
- Updates detection stats in memory

## Internal Logic

### On-Demand Flow (`execute_pipeline` in main.py)
1. Validate request body
2. Call Camera API: `GET /camera/frame/{camera_id}` → frame metadata
3. Call Detection API: `POST /detection/detect` → detection results
4. Call Usecase API: `POST /usecase/evaluate` → usecase evaluations
5. Call Alert API: `POST /alert/send` → alert status
6. Aggregate responses into single JSON response
7. Print trace statements at each step

### Continuous Flow (`_run_pipeline_once` in camera/service.py)
1. Get camera stream object from `camera_manager`
2. Get frame via `camera.get_frame()`
3. Call `detection_service.detect()` directly (not via HTTP)
4. Call `evaluate_usecases()` service function directly
5. Call `process_pipeline_alerts()` service function directly
6. Print summary to console
7. Repeat every 2 seconds until camera stops

### Key Conditions
- If frame is None, skip iteration (continuous mode) or return 503 (HTTP mode)
- If any API fails (HTTP mode), return appropriate HTTP error code
- If exception in background worker, log error and retry after 5 seconds

### Important Assumptions
- Camera must already be started before pipeline runs
- Detection service singleton exists and is initialized
- All services are thread-safe for concurrent calls
- HTTP mode uses `requests` library with 30-second timeout
- Continuous mode uses direct service calls (no HTTP overhead)

## Database Interaction

- **Read:** None directly
- **Write:** Triggers `persist_usecase_result()` via usecase service
  - Table: `usecase_results`
  - Fields: `camera_id`, `usecase_name`, `triggered`, `timestamp`

## Configuration Dependencies

- Detection confidence threshold: from request or default (0.5)
- Usecases list: from request or hardcoded ["person_in_roi", "crowd_in_roi", "restricted_zone_breach"]
- Worker sleep interval: hardcoded 2 seconds in `_pipeline_worker()`
- HTTP timeout: hardcoded 30 seconds in `execute_pipeline()`
- Base URL for HTTP calls: hardcoded `http://127.0.0.1:8000`

## Threading / Lifecycle Behavior

### Background Worker
- **Thread creation:** `CameraManager._start_pipeline_worker(camera_id)`
- **Thread name:** `pipeline-{camera_id}`
- **Daemon mode:** Yes (exits when main process exits)
- **Start trigger:** `CameraManager.start_single_camera()` after camera initialization
- **Stop trigger:** `CameraManager.stop_camera()` before camera teardown
- **Stop signal:** `threading.Event` stored in `CameraManager.pipeline_stop_events[camera_id]`
- **Graceful shutdown:** `worker.join(timeout=5.0)`
- **Execution interval:** 2 seconds (throttled via `time.sleep(2)`)
- **Error handling:** Catches all exceptions, logs, sleeps 5 seconds, continues

### Storage
- `CameraManager.pipeline_workers: Dict[str, threading.Thread]`
- `CameraManager.pipeline_stop_events: Dict[str, threading.Event]`

### Lifecycle
1. Camera starts → Worker thread spawned
2. Worker loops: run pipeline → sleep 2s → repeat
3. Camera stops → Stop event set → Worker exits within 5s
4. Thread and event removed from dicts

## Known Constraints & Decisions

### Constraints
- HTTP mode cannot call itself (would create deadlock)
- Worker runs only for single-camera mode, not multi-stream
- Only one worker per camera (duplicate check prevents multiple threads)
- Worker stops if camera object is deleted

### Tech Choices
- **HTTP for on-demand:** Preserves API independence, supports external clients
- **Direct service calls for worker:** Avoids HTTP overhead, prevents port conflicts
- **2-second interval:** Balance between responsiveness and resource usage
- **Threading over asyncio:** Simpler integration with existing sync code
- **Daemon threads:** Ensures no orphaned threads on process exit
- **5-second error backoff:** Prevents tight error loops on persistent failures

### Why This Design
- On-demand mode allows manual testing and external orchestration
- Continuous mode enables real-time monitoring without polling
- Dual implementation shows same data flow via HTTP and direct calls
- Worker tied to camera lifecycle ensures automatic cleanup

## How This Module Scales

### Multi-Camera Behavior
- One worker thread per camera (N cameras = N threads)
- Workers run independently with no shared state
- Detection service handles concurrent calls via YOLO model locking
- Database writes serialized via SQLite connection

### Multi-Usecase Behavior
- All usecases evaluated in single pipeline iteration
- No per-usecase threads (evaluated sequentially in same call)
- Adding new usecases requires updating default list in two places:
  - `_run_pipeline_once()` in camera/service.py
  - `execute_pipeline()` in main.py

### What Should NOT Be Changed Lightly
- Worker sleep interval: affects CPU/GPU load and frame processing latency
- HTTP timeout values: too low causes false failures, too high blocks event loop
- Base URL for HTTP calls: must match server binding (0.0.0.0 vs 127.0.0.1)
- Worker daemon mode: non-daemon could prevent server shutdown
- Direct vs HTTP calls in worker: mixing introduces circular dependency risk
- Error handling in worker: must never exit loop unless stop_event set

### Performance Notes
- HTTP mode: ~50-100ms overhead per API call (4 calls = 200-400ms)
- Worker mode: ~0ms overhead (direct calls), limited by detection inference time
- Bottleneck: YOLO inference (30-100ms per frame depending on GPU)
- Max throughput: ~10-30 cameras per GPU at 2-second intervals
