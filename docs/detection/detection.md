# Detection API

YOLO-based object detection with ROI intersection validation for camera streams.

## Role in Overall Pipeline

- Consumes frames from Camera Management API
- Runs YOLO inference on GPU (CUDA) with CPU fallback
- Validates detections against camera-specific ROI configuration
- Outputs structured detection results for Use Case API consumption

**Dependencies:**
- Camera Management API: provides frames and ROI configuration
- Configuration API: stores camera metadata and ROI points
- YOLO models: pre-trained weights at `sakshi/models/`

**Dependents:**
- Use Case API (future): consumes detection outputs for rule evaluation

## Inputs

### API Endpoint: POST /api/detection/process

Request payload:
```json
{
  "camera_id": "cam_001",
  "frame_data": "base64_encoded_image_string",
  "roi_id": "roi_1"
}
```

**Field constraints:**
- `camera_id`: must match existing camera in Camera API
- `frame_data`: base64-encoded JPEG/PNG image
- `roi_id`: optional, references ROI configuration from Config API

**Data sources:**
- Frames: Camera Management API (`/api/camera/frame/{camera_id}`)
- ROI points: Configuration API (polygon coordinates)

## Outputs

### Response Schema

```json
{
  "camera_id": "cam_001",
  "frame_id": "frame_12345",
  "timestamp": 1708099200.123,
  "roi_id": "roi_1",
  "detections": [
    {
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.87,
      "bbox": {
        "x": 120.5,
        "y": 340.2,
        "w": 85.3,
        "h": 210.7
      },
      "inside_roi": true
    }
  ],
  "summary": {
    "total_detections": 3,
    "detections_in_roi": 1,
    "object_present_in_roi": true
  }
}
```

**Downstream usage:**
- Use Case API subscribes to detection events
- Results stored in-memory (not persisted by Detection API)

## Internal Logic

### Detection Flow

1. Receive frame (base64) + camera_id + roi_id
2. Decode base64 → numpy array (BGR format)
3. Fetch ROI polygon points from Configuration API
4. Run YOLO inference on device (GPU/CPU)
5. For each detected bounding box:
   - Extract: class_id, class_name, confidence, bbox coords
   - Check intersection with ROI polygon using Shapely
   - Mark `inside_roi = true/false`
6. Aggregate results:
   - Count total detections
   - Count detections inside ROI
   - Set `object_present_in_roi` flag
7. Return structured response

### ROI Intersection Logic

**File:** `detection/roi.py`

```python
# Bounding box → Shapely box
bbox_polygon = box(x, y, x+w, y+h)

# ROI points → Shapely polygon
roi_polygon = Polygon(roi_points)

# Intersection check
inside_roi = bbox_polygon.intersects(roi_polygon)
```

**Decision:** Any overlap = `inside_roi = true` (not requiring full containment)

### Device Selection

**File:** `detection/device.py`

Priority order:
1. CUDA GPU (if available and torch.cuda.is_available())
2. CPU fallback

**Constraints:**
- Model loaded once at service initialization
- Device selection happens at startup, not per-frame

## Database Interaction

**None.** Detection API is stateless.

- Does NOT persist detection results
- Does NOT write to database
- Results cached in-memory for `/results/{camera_id}` endpoint (ephemeral)

**Rationale:** Use Case API or Analytics API handles persistence based on business rules.

## Configuration Dependencies

### From Configuration API

- **ROI polygon points**: `[[x1,y1], [x2,y2], [x3,y3], ...]`
  - Used for intersection validation
  - Fetched per-request via camera_id + roi_id lookup

### Environment Variables

```python
YOLO_MODEL_PATH = "sakshi/models/yolo11n.pt"  # Default model
DETECTION_CONFIDENCE_THRESHOLD = 0.25  # YOLO confidence cutoff
DETECTION_IOU_THRESHOLD = 0.45  # NMS threshold
```

### Runtime Flags

- `device`: auto-detected (cuda/cpu), not user-configurable
- `half_precision`: True if CUDA available (FP16 optimization)

## Threading / Lifecycle Behavior

**Single-threaded inference** (per request):
- Each `/process` call blocks on YOLO inference
- No background threads
- No persistent state between requests

**Service initialization:**
```python
# On server startup:
detection_service = DetectionService()  # Loads YOLO model to device
```

**Cleanup:**
- No explicit cleanup needed
- Model unloaded on process termination

## Known Constraints & Decisions

### Why GPU-only optimization?
- Industrial camera deployments assume GPU server
- CPU fallback exists but expect 10-20x slower inference

### Why stateless?
- Detection API provides raw inference results
- Use Case API decides what to persist based on rules
- Avoids duplicate storage logic

### Why base64 encoding?
- Simplifies HTTP/JSON transport
- Camera API already provides frames as base64
- Inefficient for high-FPS use cases (future: consider binary streaming)

### YOLO model choice
- `yolo11n.pt`: fastest YOLO variant (nano)
- Trade-off: speed over accuracy
- **Do NOT replace** without benchmarking FPS impact at scale

### ROI intersection vs containment
- Current: ANY overlap triggers `inside_roi = true`
- Alternative (not implemented): require bbox center inside ROI
- **Reason:** Reduce false negatives for partially visible objects

## How This Module Scales

### Multi-camera behavior
- Each camera processes independently
- No shared state between cameras
- Bottleneck: GPU memory (batch processing not implemented)

### Performance characteristics
- Single frame inference: ~30-50ms (GPU), ~300-500ms (CPU)
- Max throughput: ~20 FPS per camera (GPU), ~2-3 FPS (CPU)
- Memory: ~2GB GPU VRAM for model, ~500MB per concurrent camera

### What NOT to change

**Do NOT:**
- Switch YOLO model without profiling (breaks FPS guarantees)
- Add database writes here (violates separation of concerns)
- Make inference synchronous batch processing (breaks per-camera isolation)
- Change ROI intersection to containment (breaks existing use cases)

**Safe to change:**
- Confidence threshold (tune per deployment)
- Add detection filters (e.g., class-specific logic)
- Output schema additions (backward compatible)

### Scaling paths

**Horizontal scaling:**
- Deploy multiple Detection API instances
- Load balance by camera_id
- GPU required per instance

**Batch optimization (future):**
- Group frames from multiple cameras
- Run YOLO batch inference
- Requires Camera API to support frame buffering

## File Structure

```
detection/
├── __init__.py
├── api.py           # FastAPI routes
├── service.py       # YOLO inference engine
├── schemas.py       # Pydantic models
├── device.py        # GPU/CPU detection
└── roi.py           # Intersection logic
```

## Critical Code References

### YOLO Inference
**File:** `detection/service.py`
```python
results = self.model(frame, conf=0.25, iou=0.45, device=self.device)
```

### ROI Validation
**File:** `detection/roi.py`
```python
def check_intersection(bbox, roi_points):
    bbox_polygon = box(bbox['x'], bbox['y'], bbox['x']+bbox['w'], bbox['y']+bbox['h'])
    roi_polygon = Polygon(roi_points)
    return bbox_polygon.intersects(roi_polygon)
```

### API Integration
**File:** `detection/api.py`
```python
@router.post("/process")
async def process_detection(request: DetectionRequest):
    # Returns DetectionResponse with inside_roi flags
```

## Testing Commands

Start server:
```bash
cd /home/sanika/GOEC/yolo_clean && source bin/activate
cd ../sakshi && python main.py
```

Test detection:
```bash
curl -X POST http://localhost:8000/api/detection/process \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "cam_001",
    "frame_data": "<base64_image>",
    "roi_id": "roi_1"
  }'
```

Health check:
```bash
curl http://localhost:8000/api/detection/health
```
