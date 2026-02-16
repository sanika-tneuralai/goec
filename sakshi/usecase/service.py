"""
Usecase evaluation service.
"""
import requests
from typing import Optional, Dict, Any, List


def fetch_camera_rois(camera_id: str, config_api_url: str = "http://localhost:8000") -> Optional[List[Dict[str, Any]]]:
    """
    Fetch ROI definitions for a camera from Configuration API.
    
    Args:
        camera_id: Camera identifier
        config_api_url: Base URL of Configuration API
        
    Returns:
        List of ROI definitions or None if unavailable
    """
    print(f"[USECASE CONFIG] Attempting to fetch ROI configuration for camera_id: {camera_id}")
    print(f"[USECASE CONFIG] Configuration API URL: {config_api_url}/config/camera/{camera_id}")
    
    try:
        response = requests.get(
            f"{config_api_url}/config/camera/{camera_id}",
            timeout=2.0
        )
        print(f"[USECASE CONFIG] Configuration API response status: {response.status_code}")
        
        if response.status_code == 200:
            config = response.json()
            rois = config.get('rois', [])
            print(f"[USECASE CONFIG] ROI configuration fetched successfully")
            print(f"[USECASE CONFIG]   - Number of ROIs: {len(rois)}")
            for idx, roi in enumerate(rois):
                print(f"[USECASE CONFIG]   - ROI {idx+1}: id={roi.get('roi_id')}, type={roi.get('roi_type')}")
            return rois
        elif response.status_code == 404:
            print(f"[USECASE CONFIG] No configuration found for camera_id: {camera_id}")
            return None
        else:
            print(f"[USECASE CONFIG] Unexpected status code: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"[USECASE CONFIG] WARNING: Configuration API timeout for camera_id: {camera_id}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[USECASE CONFIG] WARNING: Configuration API connection error for camera_id: {camera_id}")
        return None
    except Exception as e:
        print(f"[USECASE CONFIG] WARNING: Failed to fetch ROI configuration: {str(e)}")
        return None


def evaluate_person_in_roi(camera_id: str, detection_output: dict) -> dict:
    """
    Evaluate usecase: If a person is detected inside ROI, trigger alert.
    
    Rule: class_name == "person" AND in_roi == true
    
    Args:
        camera_id: Camera identifier
        detection_output: Detection API response JSON
        
    Returns:
        Alert-ready payload
    """
    print(f"\n[SERVICE] ========== FUNCTION ENTRY: evaluate_person_in_roi ==========")
    print(f"[SERVICE] Input Parameters:")
    print(f"[SERVICE]   - camera_id: {camera_id}")
    print(f"[SERVICE]   - detection_output keys: {list(detection_output.keys())}")
    
    # Fetch ROI configuration from Configuration API for validation
    print(f"[SERVICE] Fetching ROI configuration from Configuration API")
    rois_config = fetch_camera_rois(camera_id)
    if rois_config:
        print(f"[SERVICE] ROI configuration available: {len(rois_config)} ROIs defined in config")
    else:
        print(f"[SERVICE] No ROI configuration found, using detection output as-is (fallback)")
    
    print(f"[SERVICE] Starting usecase evaluation for camera: {camera_id}")
    print(f"[SERVICE] Detection output received: {len(detection_output.get('detections', []))} detections")
    
    print(f"[SERVICE] Initializing usecase variables...")
    usecase_id = "person_in_roi"
    usecase_triggered = False
    matched_detections = []
    print(f"[SERVICE]   - usecase_id: {usecase_id}")
    print(f"[SERVICE]   - usecase_triggered: {usecase_triggered}")
    print(f"[SERVICE]   - matched_detections: []")
    
    # Extract detections from detection output
    detections = detection_output.get("detections", [])
    print(f"[SERVICE] Extracted {len(detections)} detections from detection_output")
    
    # Check each detection
    print(f"[SERVICE] Starting detection loop...")
    for idx, detection in enumerate(detections):
        print(f"[SERVICE] --- Processing Detection {idx+1}/{len(detections)} ---")
        class_name = detection.get("class_name", "")
        in_roi = detection.get("in_roi", False)
        confidence = detection.get("confidence", 0.0)
        
        print(f"[SERVICE]   Detection {idx+1}: class_name='{class_name}', in_roi={in_roi}, confidence={confidence}")
        
        # Check if person AND in ROI
        print(f"[SERVICE]   Checking condition: class_name == 'person' AND in_roi == True")
        print(f"[SERVICE]   class_name == 'person': {class_name == 'person'}")
        print(f"[SERVICE]   in_roi == True: {in_roi == True}")
        
        if class_name == "person" and in_roi:
            print(f"[SERVICE]   ✓✓✓ MATCH FOUND ✓✓✓")
            print(f"[SERVICE]   Person detected inside ROI - Confidence: {confidence}")
            print(f"[SERVICE]   Setting usecase_triggered = True")
            usecase_triggered = True
            matched_detections.append(detection)
            print(f"[SERVICE]   Added to matched_detections (total now: {len(matched_detections)})")
        else:
            print(f"[SERVICE]   ✗ No match - Condition not satisfied")
    
    print(f"[SERVICE] Detection loop completed")
    matched_count = len(matched_detections)
    print(f"[SERVICE] Total matched detections: {matched_count}")
    
    # Build alert-ready payload
    print(f"[SERVICE] Building alert-ready payload...")
    alert_payload = {
        "camera_id": camera_id,
        "usecase_id": usecase_id,
        "usecase_triggered": usecase_triggered,
        "matched_detections": matched_detections,
        "matched_count": matched_count
    }
    print(f"[SERVICE] Alert payload built:")
    print(f"[SERVICE]   - camera_id: {alert_payload['camera_id']}")
    print(f"[SERVICE]   - usecase_id: {alert_payload['usecase_id']}")
    print(f"[SERVICE]   - usecase_triggered: {alert_payload['usecase_triggered']}")
    print(f"[SERVICE]   - matched_count: {alert_payload['matched_count']}")
    
    print(f"[SERVICE] Evaluation complete - Triggered: {usecase_triggered}, Matched persons: {matched_count}")
    print(f"[SERVICE] Alert payload ready for transmission")
    print(f"[SERVICE] ========== FUNCTION EXIT: evaluate_person_in_roi ==========\n")
    
    return alert_payload
