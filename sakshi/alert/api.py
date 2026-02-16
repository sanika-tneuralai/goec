"""
Alert API endpoints.
"""
from fastapi import APIRouter

from alert.schemas import AlertRequest, AlertResponse
from alert.service import process_alert


router = APIRouter(prefix="/alert", tags=["alert"])


@router.post("/send", response_model=AlertResponse)
def send_alert(request: AlertRequest):
    """
    Process and send alert based on usecase evaluation.
    
    **Process:**
    1. Receives alert-ready payload from Usecase API
    2. Evaluates alert rule: usecase_id == "person_in_roi" AND alert_required == true
    3. Simulates sending alert (print-only)
    4. Returns alert status
    
    **Request Body:**
    - **camera_id**: Camera identifier
    - **usecase_id**: Usecase that triggered the alert
    - **alert_required**: Whether alert is required
    - **alert_type**: Type of alert
    - **alert_objects**: Objects that triggered the alert
    - **alert_count**: Number of objects
    
    **Response:**
    - Alert status with sent confirmation
    """
    print(f"\n[API] ============== FUNCTION ENTRY: send_alert ==============")
    print(f"[API] POST /alert/send called")
    print(f"[API] Request received for camera_id: {request.camera_id}")
    
    response = process_alert(request)
    
    print(f"[API] Preparing to return response...")
    print(f"[API] Response: {response.model_dump()}")
    print(f"[API] ============== FUNCTION EXIT: send_alert ==============\n")
    
    return response
