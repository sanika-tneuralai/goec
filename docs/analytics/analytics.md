# Analytics & Reporting Module
Real-time data persistence and aggregated analytics for detection pipeline

## Role in Overall Pipeline
- Receives detection, usecase, and alert data from existing APIs
- Persists raw operational data to PostgreSQL
- Aggregates data daily via scheduled jobs
- Exposes read-only analytics endpoints for reporting
- Does NOT block or modify detection/usecase/alert flow

**Dependencies:**
- Detection API → writes to `detections` table
- Usecase API → writes to `usecase_results` table
- Alert API → writes to `alerts` table
- Configuration API → `camera_id` as foreign key reference

**Dependents:**
- None (read-only analytics consumption)

## Inputs

### Data Sources (Write Operations)
All writes happen automatically during normal API operations:

**From Detection Service:**
```python
# After each detection
persist_detection(
    camera_id="cam_01",
    object_type="person",
    confidence=0.87,
    inside_roi=True
)
```

**From Usecase Service:**
```python
# After each usecase evaluation
persist_usecase_result(
    camera_id="cam_01",
    usecase_name="person_in_roi",
    triggered=True,
    detection_id=None  # Optional FK
)
```

**From Alert Service:**
```python
# After each alert sent
persist_alert(
    camera_id="cam_01",
    usecase_name="person_in_roi",
    alert_type="person_detected",
    status="sent"  # or "failed"
)
```

### API Requests (Read Operations)

**GET /analytics/daily**
```json
Query params:
- camera_id (optional): "cam_01"
- start_date (optional): "2026-02-01"
- end_date (optional): "2026-02-23"
```

**GET /analytics/alerts**
```json
Query params:
- camera_id (optional): "cam_01"
- start_date (optional): "2026-02-01"
- end_date (optional): "2026-02-23"
```

**GET /analytics/detections**
```json
Query params:
- camera_id (optional): "cam_01"
- start_date (optional): "2026-02-01"
- end_date (optional): "2026-02-23"
```

## Outputs

### API Responses

**Daily Analytics Response:**
```json
{
  "data": [
    {
      "date": "2026-02-23",
      "camera_id": "cam_01",
      "total_detections": 1250,
      "roi_violations": 87,
      "alerts_sent": 12
    }
  ],
  "total_records": 1
}
```

**Alert Analytics Response:**
```json
{
  "data": [
    {
      "camera_id": "cam_01",
      "usecase_name": "person_in_roi",
      "total_alerts": 45,
      "alerts_sent": 42,
      "alerts_failed": 3
    }
  ],
  "total_records": 1
}
```

**Detection Analytics Response:**
```json
{
  "data": [
    {
      "camera_id": "cam_01",
      "total_detections": 5000,
      "roi_detections": 320,
      "non_roi_detections": 4680,
      "roi_violation_rate": 6.4
    }
  ],
  "total_records": 1
}
```

### Database Writes

**Automatic Writes:**
- `cameras` → on first detection from new camera
- `detections` → every detection API call
- `usecase_results` → every usecase evaluation
- `alerts` → every alert sent/failed

**Scheduled Writes:**
- `analytics_daily` → once per day at 00:30 UTC

## Internal Logic

### Data Persistence Flow
1. Detection/Usecase/Alert APIs call persistence helpers
2. `database/persistence.py` functions insert records
3. On error: log and continue (non-blocking)
4. Camera auto-inserted with defaults if not exists

### Daily Aggregation Flow (Cron Job)
1. Trigger: 00:30 UTC daily (APScheduler)
2. Target date: yesterday (UTC)
3. Query all cameras with activity on target date
4. For each camera:
   - Count `total_detections` (all detections)
   - Count `roi_violations` (detections where `inside_roi=True`)
   - Count `alerts_sent` (alerts where `status='sent'`)
5. Insert/update `analytics_daily` using PostgreSQL UPSERT
6. Constraint: `UNIQUE(date, camera_id)`

### Analytics Query Flow
1. Receive GET request with filters
2. Build SQLAlchemy query with WHERE clauses
3. Execute aggregation at DB level (GROUP BY, COUNT, SUM)
4. Transform to Pydantic schemas
5. Return JSON

### Key Rules
- All timestamps stored in UTC
- Persistence failures do NOT crash parent APIs
- Analytics endpoints are read-only
- No raw frame data stored
- No ORM relationships used (explicit joins only)

## Database Interaction

### Schema

**cameras**
```sql
camera_id VARCHAR(255) PK
name VARCHAR(255)
location VARCHAR(255)
created_at TIMESTAMP DEFAULT NOW()
```

**detections**
```sql
detection_id SERIAL PK
camera_id VARCHAR(255) FK → cameras.camera_id
timestamp TIMESTAMP DEFAULT NOW() [INDEXED]
object_type VARCHAR(50)
confidence FLOAT
inside_roi BOOLEAN
```

**usecase_results**
```sql
result_id SERIAL PK
camera_id VARCHAR(255) FK → cameras.camera_id
usecase_name VARCHAR(100)
detection_id INTEGER FK → detections.detection_id (nullable)
triggered BOOLEAN
timestamp TIMESTAMP DEFAULT NOW() [INDEXED]
```

**alerts**
```sql
alert_id SERIAL PK
camera_id VARCHAR(255) FK → cameras.camera_id
usecase_name VARCHAR(100)
alert_type VARCHAR(50)
timestamp TIMESTAMP DEFAULT NOW() [INDEXED]
status VARCHAR(20)  -- 'sent' or 'failed'
```

**analytics_daily**
```sql
id SERIAL PK
date DATE [INDEXED]
camera_id VARCHAR(255) FK → cameras.camera_id [INDEXED]
total_detections INTEGER
roi_violations INTEGER
alerts_sent INTEGER

UNIQUE CONSTRAINT: (date, camera_id)
```

### Write Operations
- INSERT on every detection, usecase eval, alert
- INSERT OR UPDATE (upsert) for daily aggregation
- Auto-rollback on error

### Read Operations
- SELECT with date range filters
- GROUP BY for aggregations
- No table joins in analytics queries (pre-aggregated)

## Configuration Dependencies

### Environment Variables
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/goec
```

**Format:**
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**Defaults:**
- User: `postgres`
- Password: `postgres`
- Host: `localhost`
- Port: `5432`
- Database: `goec`

### PostgreSQL Requirements
- Version: 14+ (tested on 14.20)
- Extensions: None required
- Encoding: UTF-8
- Timezone: UTC recommended

### Connection Pool Settings
```python
pool_size=5
max_overflow=10
pool_pre_ping=True
```

## Threading / Lifecycle Behavior

### Scheduler Lifecycle
**Startup (in `main.py` lifespan):**
```python
from analytics.scheduler import start_scheduler
start_scheduler()
```
- Loads APScheduler BackgroundScheduler
- Registers `daily_aggregation_job` with CronTrigger
- Schedule: `hour=0, minute=30, timezone='UTC'`
- Job ID: `'daily_aggregation'`
- Starts background thread

**Shutdown:**
```python
from analytics.scheduler import stop_scheduler
stop_scheduler()
```
- Calls `scheduler.shutdown(wait=False)`
- Does NOT wait for running jobs

### Database Init
**Startup:**
```python
from database.connection import init_db
init_db()
```
- Imports all models
- Calls `Base.metadata.create_all(bind=engine)`
- Creates tables if not exist
- Tests connection
- Raises on failure (blocks startup)

### Thread Safety
- SQLAlchemy sessions: NOT shared across threads
- Each persistence call: new session via `SessionLocal()`
- Session cleanup: always in `finally` block
- Scheduler thread: isolated from FastAPI workers

## Known Constraints & Decisions

### Technology Choices
- **PostgreSQL only** (no MongoDB, Redis, etc.)
- **SQLAlchemy Core** (minimal ORM, explicit queries)
- **APScheduler** (no Celery, Airflow, external schedulers)
- **No background workers** (scheduler runs in-process)

### Data Constraints
- No raw frame storage
- No image/video persistence
- No per-detection bounding box coordinates stored
- `detection_id` FK in `usecase_results` is optional (often NULL)

### Performance Decisions
- Date fields indexed (`detections.timestamp`, `alerts.timestamp`, `analytics_daily.date`)
- `camera_id` indexed in all tables
- Aggregation at DB level (not in Python)
- No cascade deletes (manual cleanup required)

### Error Handling
- Persistence errors logged, not raised
- Detection/Usecase/Alert APIs continue on DB failure
- Analytics API returns 500 on query failure
- Scheduler errors logged, next run unaffected

### Deployment Assumptions
- PostgreSQL accessible from app host
- Single application instance (scheduler not distributed)
- UTC timezone on application server
- Database migrations NOT implemented (schema changes require manual ALTER)

## How This Module Scales

### Multi-Camera Behavior
- Each camera gets separate rows in all tables
- `analytics_daily` aggregates per camera independently
- No cross-camera queries or joins
- Foreign key: `camera_id` references `cameras.camera_id`

### Multi-Usecase Behavior
- Each usecase evaluation → separate row in `usecase_results`
- Each triggered alert → separate row in `alerts`
- Alert analytics GROUP BY `(camera_id, usecase_name)`
- No limit on number of usecases

### Performance Characteristics
**Write Load:**
- 1 camera × 5 FPS × 60s = 300 detections/min → 300 INSERTs/min
- 10 cameras = 3,000 INSERTs/min
- 100 cameras = 30,000 INSERTs/min

**Aggregation Load:**
- Daily job processes all cameras for 1 day
- Query complexity: O(cameras × days_to_aggregate)
- Runs once per day (low frequency)

**Read Load:**
- Analytics queries use indexes on `date` and `camera_id`
- No full table scans if filters applied
- Response time: <100ms for typical queries

### What Should NOT Be Changed

**Breaking Changes:**
- Renaming tables or primary key columns
- Changing `camera_id` from VARCHAR to other type
- Removing indexes on `timestamp` or `camera_id`
- Changing scheduler timezone from UTC
- Removing `pool_pre_ping=True` (handles connection drops)

**Safe Changes:**
- Adding new columns to existing tables
- Adding new analytics endpoints
- Changing aggregation schedule time
- Adding new indexes
- Increasing connection pool size

### Scaling Limits
- Single scheduler instance (not distributed)
- No partitioning (all data in single tables)
- No retention policy (data grows indefinitely)
- No real-time aggregation (24hr delay minimum)

### Future Optimization Paths
- Table partitioning by date (for large deployments)
- Materialized views for common queries
- Separate read replica for analytics queries
- Retention policy cron job (delete old data)
- Distributed scheduler (if multi-instance deployment)
