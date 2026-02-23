# Screenshot Capture & Alert Traceability
Cross-cutting feature that captures detection frames and links alerts to specific detections.

## Role in Overall Pipeline
- Captures and persists detection frames as JPEG screenshots
- Links alerts to the exact detection that triggered them via foreign key
- Enables future dashboards to display alert evidence images
- Maintains full data lineage: frame → detection → usecase → alert → screenshot

## Inputs

### Detection API
- **Frame source**: Camera stream (numpy array from camera.get_frame())
- **YOLO results**: Bounding boxes, classes, confidence scores
- **ROI data**: From camera object (roi_points, roi_mask)

### Usecase API
- **Detection output**: Complete DetectionResponse from Detection API
- **Includes**: detections[], screenshot_path, first_detection_id

### Alert API
- **Usecase results**: List of evaluated usecase outcomes
- **Includes**: usecase_id, triggered, detection_id, screenshot_path

## Outputs

### Filesystem
- **Location**: `sakshi/screenshots/`
- **Naming**: `<camera_id>_<timestamp>.jpg`
- **Timestamp format**: `YYYYMMDD_HHMMSS_ffffff` (microseconds for collision safety)
- **Format**: JPEG (OpenCV default quality)

### Detection API Response
```json
{
  "camera_id": "cam1",
  "detections": [...],
  "first_detection_id": 12345,
  "screenshot_path": "/path/to/sakshi/screenshots/cam1_20260219_143052_123456.jpg",
  "timestamp": "2026-02-19T14:30:52.123456"
}
```

### Usecase API Response
```json
{
  "camera_id": "cam1",
  "results": [
    {
      "usecase_id": "person_in_roi",
      "triggered": true,
      "detection_id": 12345,
      "screenshot_path": "/path/to/sakshi/screenshots/cam1_20260219_143052_123456.jpg"
    }
  ]
}
```

### Database Writes
- **detections table**: screenshot_path column populated
- **alerts table**: detection_id and screenshot_path columns populated
- **usecase_results table**: detection_id column populated (if triggered)

## Internal Logic

### Detection Service Flow
1. Run YOLO inference on frame
2. Parse detections and filter by ROI
3. **IF detections found**:
   - Call `_save_screenshot(frame, camera_id)`
   - Generate filename with microsecond timestamp
   - Save frame to disk using cv2.imwrite()
   - Capture screenshot_path
4. Persist detections to database:
   - Save each detection with screenshot_path
   - Capture first detection_id from first insert
5. Return DetectionResponse with:
   - first_detection_id
   - screenshot_path

### Screenshot Save Logic
```python
# File: detection/service.py → _save_screenshot()
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
filename = f"{camera_id}_{timestamp}.jpg"
filepath = os.path.join(SCREENSHOTS_DIR, filename)
cv2.imwrite(filepath, frame)
return filepath  # or None on failure
```

### Usecase Service Flow
1. Extract from detection_output:
   - screenshot_path
   - first_detection_id
2. Evaluate each usecase rule
3. Build UsecaseResult with:
   - triggered status
   - detection_id (from detection_output)
   - screenshot_path (from detection_output)
4. Persist usecase_result to database with detection_id

### Alert Service Flow
1. Iterate usecase_results
2. Extract for each result:
   - detection_id
   - screenshot_path
3. **IF triggered = True AND alert conditions met**:
   - Persist alert with:
     - camera_id
     - usecase_name
     - alert_type
     - **detection_id** (FK to detections table)
     - **screenshot_path** (same path from detection)

## Database Interaction

### Tables Modified

**detections**
```sql
detection_id         INT PRIMARY KEY AUTO_INCREMENT
camera_id            VARCHAR(255) FK → cameras.camera_id
object_type          VARCHAR(50)
confidence           FLOAT
inside_roi           BOOLEAN
screenshot_path      VARCHAR(500) NULLABLE  -- ← ADDED
timestamp            TIMESTAMP
```

**alerts**
```sql
alert_id             INT PRIMARY KEY AUTO_INCREMENT
camera_id            VARCHAR(255) FK → cameras.camera_id
usecase_name         VARCHAR(100)
alert_type           VARCHAR(50)
detection_id         INT NULLABLE FK → detections.detection_id  -- ← ADDED
screenshot_path      VARCHAR(500) NULLABLE
status               VARCHAR(20)
timestamp            TIMESTAMP
```

**usecase_results** (unchanged schema, updated writes)
```sql
result_id            INT PRIMARY KEY AUTO_INCREMENT
camera_id            VARCHAR(255) FK → cameras.camera_id
usecase_name         VARCHAR(100)
detection_id         INT NULLABLE FK → detections.detection_id
triggered            BOOLEAN
timestamp            TIMESTAMP
```

### Data Flow
1. Detection service → INSERT into detections with screenshot_path
2. Usecase service → INSERT into usecase_results with detection_id
3. Alert service → INSERT into alerts with detection_id + screenshot_path

### Query Patterns
```sql
-- Get alert with screenshot
SELECT a.*, d.screenshot_path 
FROM alerts a 
JOIN detections d ON a.detection_id = d.detection_id
WHERE a.alert_id = ?;

-- Get all alerts for a camera with images
SELECT a.*, d.screenshot_path
FROM alerts a
LEFT JOIN detections d ON a.detection_id = d.detection_id
WHERE a.camera_id = ?;
```

## Configuration Dependencies

### Required Imports
```python
# detection/service.py
import cv2
import os
from common.config import SCREENSHOTS_DIR

# common/config.py
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
```

### Environment Variables
None. Screenshot directory is hardcoded relative to BASE_DIR.

### Runtime Behavior
- Directory created on first save if not exists
- No cleanup policy implemented (manual disk management required)

## Threading / Lifecycle Behavior

### Synchronous Flow
- Screenshot save happens synchronously in detection thread
- Blocks detection response until file write completes
- Typical write time: ~5-20ms for 1920x1080 JPEG

### Failure Handling
```python
# If screenshot save fails:
try:
    screenshot_path = self._save_screenshot(frame, camera_id)
except Exception as e:
    logger.error(f"Screenshot save failed: {e}")
    screenshot_path = None  # Pipeline continues

# Detection persists with screenshot_path = None
# Alert persists with screenshot_path = None
# No pipeline breakage
```

### No Background Workers
- All file I/O is synchronous
- No async/await in screenshot logic
- No queue or delayed writes

## Known Constraints & Decisions

### Design Decisions
- **One screenshot per detection event** (not per object)
  - All detections in same frame share one screenshot
  - Reduces disk usage for multi-object frames
  
- **Screenshot triggered ONLY when detections > 0**
  - No screenshots for empty frames
  - Saves disk space and I/O

- **Reuse screenshot for alerts** (no duplicate saves)
  - Alert references detection's screenshot via detection_id
  - Alert.screenshot_path is denormalized copy for query convenience

- **Local filesystem only** (no S3/MinIO/cloud)
  - Simplifies deployment
  - Requires manual backup strategy

- **File path stored as string** (not blob)
  - Database-agnostic
  - Enables CDN/NAS migration later
  - Requires filesystem consistency

- **First detection_id used for linkage**
  - Arbitrary choice when multiple detections
  - Ensures non-null FK for triggered usecases

### Technical Limitations
- **No screenshot deduplication**
  - Multiple detections in 1 second create multiple files (microsecond diff)
  - Disk space grows linearly with detection frequency

- **No automatic cleanup**
  - Screenshot folder grows indefinitely
  - Implement cron job or retention policy separately

- **No concurrency safety**
  - Timestamp collisions possible if same camera_id processes ≥2 frames in same microsecond
  - Unlikely in practice (FPS << 1M)

- **No image compression config**
  - Uses OpenCV default JPEG quality (~95%)
  - Hardcoded in cv2.imwrite()

- **No cloud storage hooks**
  - Would require modifying _save_screenshot() only
  - Filepath return value already abstracted

### Database Constraints
- **screenshot_path is nullable**
  - Allows graceful degradation on save failure
  - Queries must handle NULL values

- **detection_id in alerts is nullable**
  - Legacy alerts may not have detection linkage
  - Future queries should LEFT JOIN

- **No cascade delete configured**
  - Deleting detection does not delete screenshot file
  - Deleting detection does not cascade to alerts
  - Manual orphan cleanup required

## How This Module Scales

### Multi-Camera Behavior
- **Thread-safe**: Each camera detection runs in separate request
- **Filename uniqueness**: camera_id prefix prevents collisions
- **Directory shared**: All cameras write to same screenshots/ folder
- **No cross-camera interference**: Independent detection flows

### Multi-Usecase Behavior
- **Screenshot shared**: All usecases for one detection reference same screenshot
- **Detection_id shared**: All triggered usecases link to same detection
- **Alert duplication**: Same screenshot_path stored in multiple alert rows (denormalized)

### Disk Space Growth
- **Linear with detection frequency**: N detections = N screenshots
- **Typical file size**: 50-200KB per JPEG (1920x1080)
- **Example**: 100 detections/hour = ~1GB/week
- **Mitigation**: Implement retention policy (delete screenshots older than N days)

### Database Growth
- **Minimal overhead**: screenshot_path is VARCHAR(500) = ~500 bytes per detection
- **Index considerations**: detection_id in alerts should be indexed for join performance
- **Partitioning strategy**: Partition by timestamp if detections table exceeds 10M rows

### What Should NOT Be Changed

#### Critical Invariants
1. **Screenshot naming must remain deterministic**
   - camera_id_timestamp.jpg format is queried by external tools
   - Changing format breaks file discovery

2. **screenshots/ directory location**
   - Hardcoded in multiple config references
   - Moving requires config update + DB migration

3. **detection_id FK relationship**
   - Alerts depend on detections.detection_id existing
   - Breaking this requires alert table redesign

4. **Synchronous save in detection flow**
   - Moving to async requires request buffering
   - Changes response timing guarantees

#### Safe to Change
- JPEG quality (modify cv2.imwrite params)
- Screenshot directory (update SCREENSHOTS_DIR config)
- Retention policy (add cleanup cron job)
- Storage backend (modify _save_screenshot() implementation)

## File Modifications Summary

### Modified Files
```
sakshi/common/config.py           # Added SCREENSHOTS_DIR
sakshi/database/models.py         # Added screenshot_path, detection_id columns
sakshi/database/persistence.py   # Updated persist_detection(), persist_alert()
sakshi/detection/schemas.py       # Added first_detection_id, screenshot_path
sakshi/detection/service.py       # Added _save_screenshot(), capture logic
sakshi/usecase/schemas.py         # Added detection_id, screenshot_path
sakshi/usecase/service.py         # Pass detection_id through flow
sakshi/alert/service.py           # Persist detection_id with alerts
```

### No New Endpoints
- No new FastAPI routes added
- No changes to existing API contracts
- Feature transparent to API consumers

### Database Migration Required
```sql
ALTER TABLE detections ADD COLUMN screenshot_path VARCHAR(500) NULL;
ALTER TABLE alerts ADD COLUMN detection_id INT NULL;
ALTER TABLE alerts ADD COLUMN screenshot_path VARCHAR(500) NULL;
ALTER TABLE alerts ADD CONSTRAINT fk_alert_detection 
    FOREIGN KEY (detection_id) REFERENCES detections(detection_id);
```

## Future Enhancements

### Recommended Additions
1. **Screenshot retention policy**
   - Cron job to delete screenshots older than 7 days
   - Update DB records to mark screenshot_path as expired

2. **Thumbnail generation**
   - Generate 200x200 thumbnails for dashboard previews
   - Store thumbnail_path alongside screenshot_path

3. **Cloud storage migration**
   - Replace _save_screenshot() with S3 upload
   - Store S3 URL in screenshot_path column
   - Maintain local fallback on S3 failure

4. **Deduplication**
   - Hash frame before save
   - Check if identical frame already exists
   - Reuse existing screenshot_path

5. **Compression options**
   - Add JPEG_QUALITY config parameter
   - Support WebP for better compression
   - Add resolution downscaling option

### Not Recommended
- Storing images as BLOBs in PostgreSQL (poor performance at scale)
- Per-alert screenshot duplication (waste of disk space)
- Synchronous cloud uploads (breaks pipeline on network issues)
