# Alert API
Final step in detection pipeline - processes alert-ready payloads and simulates alert sending

## Role in Overall Pipeline
- Receives alert-ready payload from Usecase API
- Evaluates alert rule to determine if alert should be sent
- Simulates alert sending (print-only, no real notifications)
- Terminal endpoint - nothing depends on this module's output
- **Upstream dependency**: Usecase API (provides alert-ready payload)
- **Downstream dependency**: None (terminal module)

## Inputs

### API Endpoint
```
POST /alert/send
```

### Request Schema (AlertRequest)
```json
{
  "camera_id": "s1_cam_1",
  "usecase_id": "person_in_roi",
  "alert_required": true,
  "alert_type": "PERSON_IN_ROI",
  "alert_objects": [
    {
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.9015623927116394,
      "bbox": {
        "x1": 682.6243286132812,
        "y1": 188.95413208007812,
        "x2": 1011.93017578125,
        "y2": 752.4739990234375
      },
      "in_roi": true
    }
  ],
  "alert_count": 1
}
```

### Field Mapping from Usecase API Output
- `usecase_triggered` → `alert_required`
- `matched_detections` → `alert_objects`
- `matched_count` → `alert_count`
- Add constant: `alert_type: "PERSON_IN_ROI"`

### Data Source
- Usecase API endpoint: `POST /usecase/evaluate`
- Manual transformation required (no automatic mapping implemented)

## Outputs

### Response Schema (AlertResponse)
```json
{
  "camera_id": "s1_cam_1",
  "alert_sent": true,
  "alert_type": "PERSON_IN_ROI",
  "alert_count": 1,
  "message": "Person detected inside ROI. Alert sent."
}
```

### Console Output (print statements)
```
[API] ============== FUNCTION ENTRY: send_alert ==============
[API] POST /alert/send called
[SERVICE] Evaluating alert rule...
[ALERT] ⚠️  ALERT TRIGGERED ⚠️
[ALERT] Camera: s1_cam_1
[ALERT] Type: PERSON_IN_ROI
[ALERT] Objects detected: 1
```

### Events Triggered
- None (no webhooks, no database writes, no downstream API calls)

## Internal Logic

### Single Service Function: `process_alert()`
1. Receive AlertRequest payload
2. Print received payload details
3. Evaluate alert rule:
   - Check: `usecase_id == "person_in_roi"`
   - Check: `alert_required == true`
   - Both must be true
4. If rule matches:
   - Print alert simulation message with camera_id, alert_type, alert_count
   - Set `alert_sent = true`
   - Set message: "Person detected inside ROI. Alert sent."
5. If rule does not match:
   - Set `alert_sent = false`
   - Set message: "Alert conditions not met. No alert sent."
6. Return AlertResponse

### Alert Rule (ONLY RULE)
```python
if request.usecase_id == "person_in_roi" and request.alert_required:
    # Send alert
```

### Critical Assumptions
- No retry logic for failed alerts
- No persistence of alert history
- No rate limiting or deduplication
- No multi-usecase support (only "person_in_roi")
- Synchronous processing only

## Database Interaction
None. This module does not read from or write to any database.

## Configuration Dependencies
None. No runtime configuration required. Alert rule is hardcoded.

## Threading / Lifecycle Behavior
- Synchronous API endpoint (no background threads)
- No lifecycle management required
- No cleanup needed
- No startup/shutdown hooks

## Known Constraints & Decisions

### Scope Constraints
- Print-only alert simulation (no real SMS, email, push notifications)
- Single hardcoded alert rule
- No background workers or schedulers
- No queue system
- No retry mechanism

### Tech Choices
- Uses `print()` for debugging (not logging module)
- Follows FastAPI sync pattern (not async)
- Linear service function (no abstraction layers)
- Pydantic schemas for validation

### Limitations
- Manual payload transformation required from Usecase API
- No alert history tracking
- No alert acknowledgment mechanism
- No multi-channel alert routing
- Cannot handle multiple usecase types without code modification

## How This Module Scales

### Multi-Camera Behavior
- Stateless - handles each camera independently
- No per-camera alert configuration
- Same alert rule applies to all cameras
- No camera-specific rate limiting

### Multi-Usecase Behavior
- Currently supports ONLY "person_in_roi" usecase
- Adding new usecases requires:
  - Code modification in `process_alert()` function
  - Additional if/elif conditions for new usecase_id values
  - No plugin/rule-engine architecture exists

### What Should NOT Be Changed Lightly
- Alert rule logic location (alert/service.py)
- Request/response schema field names (breaks Usecase API contract)
- Print statement format (used for debugging/tracing)
- Synchronous processing model (no async without FastAPI changes)

## File Structure
```
alert/
├── __init__.py          # Module marker
├── schemas.py           # AlertRequest, AlertResponse (Pydantic)
├── service.py           # process_alert() function
└── api.py               # FastAPI router, POST /alert/send endpoint
```

## Integration Point in main.py
```python
from alert.api import router as alert_router
app.include_router(alert_router)
```

## Testing Commands

### Direct API Test
```bash
curl -X POST http://localhost:8000/alert/send \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "s1_cam_1",
    "usecase_id": "person_in_roi",
    "alert_required": true,
    "alert_type": "PERSON_IN_ROI",
    "alert_objects": [{"class_name": "person", "in_roi": true}],
    "alert_count": 1
  }'
```

### Full Pipeline Test
```bash
# 1. Detection
DETECTION=$(curl -s -X POST http://localhost:8000/detection/detect \
  -H "Content-Type: application/json" \
  -d '{"camera_id": "s1_cam_1"}')

# 2. Usecase Evaluation
USECASE=$(curl -s -X POST http://localhost:8000/usecase/evaluate \
  -H "Content-Type: application/json" \
  -d "{\"camera_id\": \"s1_cam_1\", \"detection_output\": $DETECTION}")

# 3. Manual transformation required here (jq or manual edit)
# Transform usecase_triggered → alert_required, etc.

# 4. Send Alert
curl -X POST http://localhost:8000/alert/send \
  -H "Content-Type: application/json" \
  -d "$TRANSFORMED_PAYLOAD"
```

## Future Extension Points (Not Implemented)

### If Real Alerting Required
- Add alert channel abstraction (email, SMS, webhook)
- Add alert history database table
- Add rate limiting per camera/usecase
- Add alert acknowledgment endpoint
- Add configuration-driven alert rules

### If Multi-Usecase Support Required
- Replace hardcoded rule with rule engine
- Move alert rules to Configuration API
- Add per-usecase alert channel mapping
- Add usecase-specific alert templates
