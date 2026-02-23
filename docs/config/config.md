# Configuration Management API

Single source of truth for camera configurations: ROIs, thresholds, detection models.

## Role in Overall Pipeline

**What this module does:**
- Stores and serves camera-specific configuration
- Manages ROI definitions per camera
- Manages confidence thresholds per camera
- Maps cameras to detection models

**What it depends on:**
- Nothing (standalone service)

**What depends on it:**
- Detection API (fetches confidence_threshold, detection_model, ROI count)
- Usecase API (fetches ROI definitions for validation)

## Inputs

**API Endpoints:**

### POST /config/camera
Creates or updates camera configuration.

```json
{
  "camera_id": "s1_cam_1",
  "rois": [
    {
      "roi_id": "roi_1",
      "roi_type": "bbox",
      "roi_data": {
        "x": 100.0,
        "y": 150.0,
        "width": 200.0,
        "height": 300.0
      }
    },
    {
      "roi_id": "roi_2",
      "roi_type": "polygon",
      "roi_data": {
        "points": [[10, 10], [100, 10], [100, 100], [10, 100]]
      }
    }
  ],
  "confidence_threshold": 0.7,
  "detection_model": "yolov8n"
}
```

### GET /config/camera/{camera_id}
Retrieves specific camera configuration.

### GET /config/cameras
Retrieves all camera configurations.

**Source of data:**
- External client (Postman, frontend, admin tool)
- No automatic population

## Outputs

**Response Schema (POST & GET /config/camera/{camera_id}):**

```json
{
  "camera_id": "s1_cam_1",
  "rois": [
    {
      "roi_id": "roi_1",
      "roi_type": "bbox",
      "roi_data": {
        "x": 100.0,
        "y": 150.0,
        "width": 200.0,
        "height": 300.0
      }
    }
  ],
  "confidence_threshold": 0.7,
  "detection_model": "yolov8n"
}
```

**Response Schema (GET /config/cameras):**

```json
{
  "cameras": [
    {
      "camera_id": "s1_cam_1",
      "rois": [...],
      "confidence_threshold": 0.7,
      "detection_model": "yolov8n"
    }
  ],
  "total": 1
}
```

**Events triggered:**
- None (no downstream triggers)

## Internal Logic

**Core flow:**

1. **Create/Update (POST /config/camera):**
   - Validate request via Pydantic schemas
   - Create CameraConfigResponse object
   - Store in `_camera_configs` dict with camera_id as key
   - Return stored config

2. **Retrieve Single (GET /config/camera/{camera_id}):**
   - Look up camera_id in `_camera_configs`
   - Return config or 404 if not found

3. **Retrieve All (GET /config/cameras):**
   - Convert all values from `_camera_configs` to list
   - Return with total count

**Key conditions:**
- ROI validation: `roi_type` must be "bbox" or "polygon"
- Polygon: minimum 3 points, each point exactly 2 coordinates
- BoundingBox: width and height must be > 0
- confidence_threshold: must be 0.0 to 1.0

**Important assumptions:**
- camera_id is unique identifier
- Updates overwrite entire config (no partial updates)
- No authentication/authorization required
- Configuration persists only in memory (lost on restart)

## Database Interaction

**None.** In-memory storage only.

**Storage structure:**
```python
_camera_configs: Dict[str, CameraConfigResponse] = {}
```

Key = camera_id (str)
Value = CameraConfigResponse object

## Configuration Dependencies

**None.** This module IS the configuration source.

**No environment variables required.**

**Default values:**
- confidence_threshold: 0.5 (if not provided)
- detection_model: "yolov8n" (if not provided)
- rois: [] (empty list if not provided)

## Threading / Lifecycle Behavior

**No background threads.**

**Storage lifecycle:**
- Initialized as empty dict on module import
- Persists for application lifetime
- Cleared on application restart
- No cleanup required

**Concurrency:**
- In-memory dict (not thread-safe by design)
- FastAPI handles request isolation
- No race condition protection (acceptable for current scale)

## Known Constraints & Decisions

**Constraints:**
- No database persistence (deliberate choice for v1)
- No authentication (external responsibility)
- No audit log of configuration changes
- No versioning of configurations
- No bulk import/export
- No configuration validation against running cameras

**Tech choices:**
- **Pydantic v2** for schema validation
- **In-memory dict** instead of database for simplicity
- **Separate ROI types** (bbox vs polygon) for flexibility
- **Union type for roi_data** to support multiple ROI formats
- **Optional fields with defaults** for easier API usage

**Why these choices:**
- Simplicity: no database setup required
- Speed: in-memory access is instant
- Iteration: easy to migrate to DB later without API changes
- Validation: Pydantic catches errors before storage

## How This Module Scales

**Multi-camera behavior:**
- Each camera_id gets independent configuration
- No limit on number of cameras in memory
- Linear memory growth: ~1-2KB per camera config
- Expected to handle 100+ cameras easily

**Multi-usecase behavior:**
- Not applicable (configuration is usecase-agnostic)
- Usecase logic lives in usecase API, not here

**What should NOT be changed lightly:**

1. **API response schemas** - Detection and Usecase APIs depend on exact structure
2. **camera_id as string** - used as dict key throughout system
3. **ROI schema structure** - Detection API parses this format
4. **Default values** (0.5, yolov8n) - other modules assume these fallbacks

**Migration to database:**
- Replace `_camera_configs` dict with DB queries
- Keep service function signatures identical
- Update `create_or_update_camera_config()` to use INSERT/UPDATE
- Update `get_camera_config()` to use SELECT
- Update `get_all_camera_configs()` to use SELECT with pagination
- API layer remains unchanged

## Integration Points

**Detection API integration (detection/api.py):**

Location: `detect_objects()` endpoint

```python
# Before detection runs
camera_config = fetch_camera_config(camera_id)

# Priority: Config API > Request > Default
if camera_config and 'confidence_threshold' in camera_config:
    confidence_threshold = camera_config['confidence_threshold']
else:
    confidence_threshold = request.confidence_threshold
```

**HTTP call details:**
- URL: `GET http://localhost:8000/config/camera/{camera_id}`
- Timeout: 2 seconds
- Failure handling: Falls back to request parameter
- No retry logic

**Usecase API integration (usecase/service.py):**

Location: `evaluate_person_in_roi()` function

```python
# For validation/logging only
rois_config = fetch_camera_rois(camera_id)
if rois_config:
    print(f"ROI configuration available: {len(rois_config)} ROIs")
```

**HTTP call details:**
- URL: `GET http://localhost:8000/config/camera/{camera_id}`
- Timeout: 2 seconds
- Failure handling: Logs warning, continues with detection output
- Used for validation only (detection output already has in_roi flags)

## File Structure

```
sakshi/config/
├── __init__.py          # Exports router
├── api.py               # FastAPI endpoints
├── schemas.py           # Pydantic models
└── service.py           # Business logic + in-memory storage
```

**Registered in main.py:**
```python
from config.api import router as config_router
app.include_router(config_router)
```

## Debugging

**Print statements added at:**
- API entry points (api.py)
- Service function calls (service.py)
- Before returning responses
- Configuration fetch attempts (detection/api.py, usecase/service.py)

**Format:**
- `[CONFIG API]` - API layer logs
- `[CONFIG SERVICE]` - Service layer logs
- `[DETECTION CONFIG]` - Detection API fetching config
- `[USECASE CONFIG]` - Usecase API fetching config

## Testing via Postman

**1. Create config:**
POST http://localhost:8000/config/camera
Body: Raw JSON (see Inputs section)

**2. Get config:**
GET http://localhost:8000/config/camera/s1_cam_1

**3. Get all:**
GET http://localhost:8000/config/cameras

**Expected behavior:**
- First GET returns 404 if config not created
- POST creates and returns 201
- Subsequent GETs return 200 with config
- Server restart clears all configs

## Future Considerations

**When to add database:**
- Need for persistence across restarts
- Configuration audit trail required
- Multi-instance deployment (shared state)

**When to add caching:**
- Config API response time > 50ms consistently
- Detection API timeout issues appear
- Config rarely changes but frequently read

**When to add validation:**
- Validate camera_id against running cameras
- Validate ROI coordinates against frame dimensions
- Validate detection_model against available models

**When to add versioning:**
- Need to rollback configuration changes
- A/B testing different configurations
- Scheduled configuration changes
