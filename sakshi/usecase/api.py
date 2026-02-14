"""
Usecase API endpoints.
"""
from fastapi import APIRouter, HTTPException

from usecase.schemas import UsecaseRequest, UsecaseResponse
from usecase.service import evaluate_person_in_roi


router = APIRouter(prefix="/usecase", tags=["usecase"])


@router.post("/evaluate", response_model=UsecaseResponse)
def evaluate_usecase(request: UsecaseRequest):
    """
    Evaluate usecase: Person in ROI.
    
    **Process:**
    1. Takes detection API output as input
    2. Checks if any detection has class_name == "person" AND in_roi == true
    3. Returns alert-ready payload
    
    **Request Body:**
    - **camera_id**: Camera identifier
    - **detection_output**: Complete detection API response JSON
    
    **Response:**
    - Alert-ready payload with matched person detections
    """
    print(f"\n[API] ============== FUNCTION ENTRY: evaluate_usecase ==============")
    print(f"[API] Endpoint: POST /usecase/evaluate")
    print(f"[API] Request received at usecase evaluation endpoint")
    print(f"[API] Request details:")
    print(f"[API]   - camera_id: {request.camera_id}")
    print(f"[API]   - detection_output type: {type(request.detection_output)}")
    print(f"[API]   - detection_output keys: {list(request.detection_output.keys()) if isinstance(request.detection_output, dict) else 'N/A'}")
    
    num_detections = len(request.detection_output.get('detections', [])) if isinstance(request.detection_output, dict) else 0
    print(f"[API]   - Number of detections in input: {num_detections}")
    print(f"[API] === Usecase Evaluation Started ===")
    
    try:
        print(f"[API] Calling service function: evaluate_person_in_roi()")
        print(f"[API] Passing parameters:")
        print(f"[API]   - camera_id: {request.camera_id}")
        print(f"[API]   - detection_output: {num_detections} detections")
        
        # Call service to evaluate usecase
        alert_payload = evaluate_person_in_roi(
            camera_id=request.camera_id,
            detection_output=request.detection_output
        )
        
        print(f"[API] Service function returned successfully")
        print(f"[API] Alert payload received from service:")
        print(f"[API]   - usecase_triggered: {alert_payload['usecase_triggered']}")
        print(f"[API]   - matched_count: {alert_payload['matched_count']}")
        print(f"[API]   - usecase_id: {alert_payload['usecase_id']}")
        print(f"[API] Alert payload generated - Triggered: {alert_payload['usecase_triggered']}, Persons: {alert_payload['matched_count']}")
        print(f"[API] === Returning Alert-Ready Payload ===")
        print(f"[API] Response status: 200 OK")
        print(f"[API] ============== FUNCTION EXIT: evaluate_usecase ==============\n")
        
        return alert_payload
        
    except Exception as e:
        print(f"[API] !!!!! EXCEPTION CAUGHT !!!!!")
        print(f"[API] ERROR: Usecase evaluation failed")
        print(f"[API] Exception type: {type(e).__name__}")
        print(f"[API] Exception message: {str(e)}")
        print(f"[API] Raising HTTPException with status 500")
        print(f"[API] ============== FUNCTION EXIT: evaluate_usecase (ERROR) ==============\n")
        raise HTTPException(status_code=500, detail=f"Usecase evaluation failed: {str(e)}")
