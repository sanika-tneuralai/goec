"""
Usecase API endpoints - database-driven camera-to-usecase dispatcher.
"""
from fastapi import APIRouter, HTTPException

from usecase.schemas import UsecaseRequest, UsecaseResponse
from usecase.service import evaluate_usecases


router = APIRouter(prefix="/usecase", tags=["usecase"])


@router.post("/evaluate", response_model=UsecaseResponse)
def evaluate_usecase(request: UsecaseRequest):
    """
    Evaluate usecases for a camera using database-driven configuration.
    
    **Database-Driven Usecase Dispatcher:**
    - Accepts camera_id and detection output
    - Queries database for enabled usecases for that camera
    - Evaluates all enabled usecases on the detection data
    - Returns aggregated results
    
    **Process:**
    1. Query `usecase_config` table for camera's enabled usecases
    2. Route detection data to appropriate usecase handlers
    3. Return results for all evaluated usecases
    
    **Request Body:**
    - **camera_id**: Camera identifier
    - **detection_output**: Complete detection API response JSON
    
    **Response:**
    - **camera_id**: Camera identifier
    - **results**: List of results, one per enabled usecase
    
    **Configuration:**
    - Usecases are configured in the `usecase_config` table
    - Each camera can have multiple enabled usecases
    - Adding a new camera requires only database configuration
    - Adding a new usecase requires only registering a handler
    
    **Example Request:**
    ```json
    {
      "camera_id": "s1_cam_1",
      "detection_output": {...}
    }
    ```
    """
    print(f"\n[USECASE API] ==========================================================")
    print(f"[USECASE API] DATABASE-DRIVEN USECASE EVALUATION")
    print(f"[USECASE API] ==========================================================")
    print(f"[USECASE API] Endpoint: POST /usecase/evaluate")
    print(f"[USECASE API] Camera ID: {request.camera_id}")
    
    num_detections = len(request.detection_output.get('detections', [])) if isinstance(request.detection_output, dict) else 0
    print(f"[USECASE API] Detection output: {num_detections} detection(s)")
    print(f"[USECASE API] Dispatching to database-driven usecase service...")
    print(f"[USECASE API] ==========================================================\n")
    
    try:
        # Call database-driven usecase dispatcher
        result = evaluate_usecases(
            camera_id=request.camera_id,
            detection_output=request.detection_output
        )
        
        print(f"\n[USECASE API] ==========================================================")
        print(f"[USECASE API] DISPATCHER COMPLETED")
        print(f"[USECASE API] ==========================================================")
        print(f"[USECASE API] Results received: {len(result['results'])} usecase(s)")
        
        triggered_count = sum(1 for r in result['results'] if r.triggered)
        print(f"[USECASE API] Triggered usecases: {triggered_count}/{len(result['results'])}")
        
        for uc_result in result['results']:
            status = "✓ TRIGGERED" if uc_result.triggered else "✗ Not triggered"
            print(f"[USECASE API]   - {uc_result.usecase_id}: {status} ({uc_result.matched_count} matches)")
        
        print(f"[USECASE API] Response status: 200 OK")
        print(f"[USECASE API] ==========================================================\n")
        
        return result
        
    except Exception as e:
        print(f"\n[USECASE API] !!!!! EXCEPTION CAUGHT !!!!!")
        print(f"[USECASE API] ERROR: Usecase evaluation failed")
        print(f"[USECASE API] Exception type: {type(e).__name__}")
        print(f"[USECASE API] Exception message: {str(e)}")
        print(f"[USECASE API] Raising HTTPException with status 500")
        print(f"[USECASE API] ==========================================================\n")
        raise HTTPException(status_code=500, detail=f"Usecase evaluation failed: {str(e)}")

