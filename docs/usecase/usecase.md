# Usecase API

Scalable rule-based evaluation layer that applies business logic on top of detection output to determine which alerts should be triggered.

## Role in Overall Pipeline

**What this module does:**
- Consumes detection output (detections with in_roi flags)
- Applies multiple usecase rules independently
- Returns which usecases were triggered and matched objects
- Designed to scale from 1 to 30+ usecases

**Dependencies (upstream):**
- Detection API: provides detection_output with in_roi flags already computed
- Configuration API: ROI definitions (consumed by Detection API, not directly by Usecase)

**Downstream consumers:**
- Alert API: consumes usecase results to send notifications
- Analytics: can consume usecase results for reporting
- Detection API: auto-triggers usecase evaluation after each detection

## Inputs

**API Endpoint:**
```
POST /usecase/evaluate
```

**Request Schema:**
```json
{
  "camera_id": "s1_cam_1",
  "detection_output": {
    "camera_id": "s1_cam_1",
    "timestamp": "2026-02-17T10:00:00",
    "frame_count": 100,
    "detections": [
      {
        "class_id": 0,
        "class_name": "person",
        "confidence": 0.95,
        "bbox": {
          "x1": 100,
          "y1": 100,
          "x2": 200,
          "y2": 300
        },
        "in_roi": true
      }
    ],
    "roi_detections_count": 1,
    "total_detections_count": 1,
    "processing_time_ms": 25.5
  },
  "usecases": ["person_in_roi", "crowd_in_roi", "restricted_zone_breach"]
}
```

**Required Fields:**
- `camera_id`: string
- `detection_output`: complete Detection API response (must include detections with in_roi flags)
- `usecases`: array of usecase IDs (min 1)

**Data Source:**
- Detection output is computed ONCE by Detection API
- Usecase API consumes detection output without modification
- in_roi flags are pre-computed by Detection API using ROI from Configuration API

## Outputs

**Response Schema:**
```json
{
  "camera_id": "s1_cam_1",
  "results": [
    {
      "usecase_id": "person_in_roi",
      "triggered": true,
      "matched_count": 2,
      "matched_objects": [...]
    },
    {
      "usecase_id": "crowd_in_roi",
      "triggered": false,
      "matched_count": 0,
      "matched_objects": []
    }
  ]
}
```

**Response contains:**
- One result per requested usecase
- Each result is independent
- Failed/unknown usecases are skipped (logged, not returned)

**Events triggered:**
- None directly
- Alert API consumes this response to trigger notifications
- Detection API calls this automatically (results logged, not returned to client)

## Internal Logic

**Execution flow:**
1. API receives request with camera_id, detection_output, usecases list
2. Validates request (400 if no usecases specified)
3. Calls orchestrator: `evaluate_usecases(camera_id, detection_output, usecases)`
4. Orchestrator loops through each usecase:
   - Looks up rule class from registry
   - Instantiates rule
   - Calls `rule.evaluate(detection_output)`
   - Collects result
   - Catches errors, skips failed usecases
5. Returns aggregated results for all usecases

**Orchestrator (`usecase/service.py`):**
- Takes ONE detection output
- Evaluates MULTIPLE usecases on same data
- No usecase can modify detection_output
- Errors in one usecase don't fail others

**Rule Registry (`usecase/rules/__init__.py`):**
```python
USECASE_REGISTRY = {
    "person_in_roi": PersonInROIRule,
    "crowd_in_roi": CrowdInROIRule,
    "restricted_zone_breach": RestrictedZoneRule,
}
```

**Rule Execution:**
- Each rule extends `BaseUsecaseRule`
- Implements `evaluate(detection_output)` method
- Returns: `{"triggered": bool, "matched_objects": list}`
- Rules are stateless, in-memory only

## Folder Structure

```
usecase/
├── __init__.py
├── api.py                      # Single endpoint: POST /evaluate
├── schemas.py                  # Request/Response models
├── service.py                  # Orchestrator: evaluate_usecases()
└── rules/
    ├── __init__.py             # USECASE_REGISTRY and get_usecase_rule()
    ├── base.py                 # BaseUsecaseRule (abstract class)
    ├── person_in_roi.py        # Person in ROI rule
    ├── crowd_in_roi.py         # Crowd (3+ persons) in ROI rule
    └── restricted_zone.py      # Vehicle in restricted zone rule
```

## Current Usecases

**1. person_in_roi**
- Triggers when: ANY person with in_roi == true
- Rule: `class_name == "person" AND in_roi == true`
- Use: General person detection in monitored zone

**2. crowd_in_roi**
- Triggers when: 3+ persons with in_roi == true
- Rule: `class_name == "person" AND in_roi == true AND count >= 3`
- Threshold: `CROWD_THRESHOLD = 3`
- Use: Crowd detection, social distancing violations

**3. restricted_zone_breach**
- Triggers when: ANY vehicle with in_roi == true
- Rule: `class_name in ["car", "truck", "bus", "motorcycle", "bicycle", "bike"] AND in_roi == true`
- Use: No-vehicle zones, pedestrian areas

## Adding New Usecases

**Steps (NO existing code changes required):**

1. Create new file: `usecase/rules/my_usecase.py`
   ```python
   from typing import Dict, Any
   from usecase.rules.base import BaseUsecaseRule

   class MyUsecaseRule(BaseUsecaseRule):
       def evaluate(self, detection_output: Dict[str, Any]) -> Dict[str, Any]:
           detections = self.get_detections(detection_output)
           matched_objects = []
           
           for detection in detections:
               # Your rule logic here
               if condition_met:
                   matched_objects.append(detection)
           
           triggered = len(matched_objects) > 0
           
           return {
               "triggered": triggered,
               "matched_objects": matched_objects
           }
   ```

2. Register in `usecase/rules/__init__.py`:
   ```python
   from usecase.rules.my_usecase import MyUsecaseRule
   
   USECASE_REGISTRY = {
       "my_usecase_id": MyUsecaseRule,
       # ... existing usecases
   }
   ```

3. Use in requests:
   ```json
   {
     "usecases": ["my_usecase_id"]
   }
   ```

**Rule Implementation Contract:**
- Must extend `BaseUsecaseRule`
- Must implement `evaluate(detection_output)` method
- Must return dict with: `triggered` (bool), `matched_objects` (list)
- Cannot access camera streams directly
- Cannot access ROI geometry (only in_roi flags)
- Cannot call external APIs
- Must be stateless and in-memory only

## Configuration Dependencies

**From Configuration API:**
- NONE directly
- ROI definitions are fetched by Detection API
- Detection API computes in_roi flags
- Usecase API only consumes pre-computed in_roi flags

**Runtime Configuration:**
- Usecases to evaluate can be specified per request
- Detection API auto-triggers: `["person_in_roi", "crowd_in_roi", "restricted_zone_breach"]`
- Future: per-camera usecase configuration (not implemented)

**No environment variables or config files used.**

## Detection API Integration

**Auto-trigger behavior (`detection/api.py`):**
```python
# After detection completes:
usecases_to_evaluate = ["person_in_roi", "crowd_in_roi", "restricted_zone_breach"]
usecase_result = evaluate_usecases(
    camera_id=request.camera_id,
    detection_output=detection_output,
    usecases=usecases_to_evaluate
)
# Results logged, not returned to client
```

**Key points:**
- Detection API calls usecase evaluation automatically
- Usecase failures don't break detection response
- Usecase results are logged only (not added to detection response)
- Detection API response format is unchanged

## Database Interaction

**None.**
- Usecase API is stateless
- No reads or writes to database
- Alert API (downstream) handles persistence

## Threading / Lifecycle Behavior

**Execution model:**
- Synchronous execution (not async)
- No background threads
- No long-running processes
- Each request is independent

**Startup:**
- Rules are registered at module import
- No initialization required

**Shutdown:**
- No cleanup needed
- Stateless design

## Known Constraints & Decisions

**Performance constraints:**
- Detection must run ONCE per frame
- All usecases consume same detection output
- No duplicate detection calls allowed
- All rule evaluation is in-memory

**Design decisions:**
- Detection API remains usecase-agnostic
- ROI ownership: Configuration API (definitions) → Detection API (computation) → Usecase API (consumption only)
- Usecase API NEVER recalculates ROI geometry
- Rules cannot modify detection_output
- Failed usecases are skipped, not reported as errors

**Technical constraints:**
- Uses print() for debugging (not logging framework)
- Pydantic BaseModel for schemas
- FastAPI router for endpoint
- No async operations (synchronous only)

## How This Module Scales

**Multi-camera behavior:**
- Each camera can evaluate different usecases (request-level control)
- Same usecase code works for all cameras
- No camera-specific logic in rules
- Future: per-camera usecase configuration in Configuration API

**Multi-usecase behavior:**
- Evaluate 1 to 30+ usecases in single request
- All usecases run on same detection output
- Adding usecase = add ONE file to rules/
- No changes to API, schemas, or orchestrator needed
- Registry automatically discovers new rules

**Scaling considerations:**
- Detection is bottleneck, not usecase evaluation
- In-memory rule evaluation is fast (< 1ms per usecase)
- 30+ usecases on same detection: still faster than re-running detection once

**What NOT to change:**
- Do NOT make usecases recalculate ROI
- Do NOT make usecases call Detection API
- Do NOT add state to rules (must remain stateless)
- Do NOT change detection_output format (breaks all usecases)
- Do NOT add database calls to rules (breaks performance model)

## Debugging

**Print statement locations:**
- `[API]`: API entry/exit, request validation, response assembly
- `[ORCHESTRATOR]`: Multi-usecase coordination, usecase loop, result aggregation
- `[REGISTRY]`: Rule lookup, registration errors
- `[RULE:usecase_id]`: Per-usecase evaluation, condition checks, matches

**Example debug output:**
```
[API] POST /usecase/evaluate - Camera: s1_cam_1, Usecases: 3
[ORCHESTRATOR] Evaluating 3 usecases on 5 detections
[REGISTRY] Looking up: person_in_roi
[RULE:person_in_roi] Detection 1: class='person', in_roi=True
[RULE:person_in_roi] ✓✓✓ MATCH
[ORCHESTRATOR] person_in_roi: TRIGGERED (2 matches)
```

**Debug strategy:**
- Each function prints entry/exit
- Each detection prints class_name, in_roi, confidence
- Matches are marked with ✓✓✓
- Failed conditions show ✗

## File Paths

**Module location:**
```
/home/sanika/GOEC/sakshi/usecase/
```

**Key files:**
- `api.py`: FastAPI router, single endpoint
- `schemas.py`: UsecaseRequest, UsecaseResponse, UsecaseResult
- `service.py`: evaluate_usecases() orchestrator
- `rules/__init__.py`: USECASE_REGISTRY, get_usecase_rule()
- `rules/base.py`: BaseUsecaseRule abstract class
- `rules/*.py`: Individual usecase implementations

## Testing

**Postman test structure:**
```json
POST http://localhost:8000/usecase/evaluate
Content-Type: application/json

{
  "camera_id": "s1_cam_1",
  "detection_output": { ... full detection response ... },
  "usecases": ["person_in_roi", "crowd_in_roi"]
}
```

**Test cases:**
- Single usecase evaluation
- Multiple usecases (all 3)
- Empty detections (no triggers)
- Detections outside ROI (in_roi=false, no triggers)
- Invalid usecase ID (skipped, not error)
- No usecases specified (400 error)

**Swagger UI:**
```
http://localhost:8000/docs#/usecase/evaluate_usecase_usecase_evaluate_post
```

## Integration Points

**Detection API → Usecase API:**
- Detection API imports: `from usecase.service import evaluate_usecases`
- Called after detection completes
- Results logged, not returned to client

**Usecase API → Alert API:**
- Alert API consumes usecase results
- Not implemented in this module
- Future integration point

**Configuration API → Usecase API:**
- No direct integration
- ROI definitions flow: Config API → Detection API → Usecase API (via in_roi flags)
