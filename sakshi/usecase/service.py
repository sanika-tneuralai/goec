"""
Usecase evaluation service.
"""


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
