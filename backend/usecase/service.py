"""
Usecase evaluation service - database-driven camera-to-usecase dispatcher.
"""
from typing import Dict, Any, List
from usecase.rules import get_usecase_rule
from usecase.schemas import UsecaseResult
from database.persistence import get_enabled_usecases, persist_usecase_result


def evaluate_usecases(camera_id: str, detection_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate usecases for a camera using database-driven configuration.
    
    This dispatcher:
    - Queries database for enabled usecases for the given camera
    - Routes detection data to appropriate usecase handlers
    - Returns aggregated results
    
    Args:
        camera_id: Camera identifier
        detection_output: Detection API response
        
    Returns:
        Dictionary containing:
            - camera_id: Camera identifier
            - results: List of UsecaseResult objects
    """
    print(f"\n[USECASE DISPATCHER] ====================================================")
    print(f"[USECASE DISPATCHER] DATABASE-DRIVEN USECASE EVALUATION")
    print(f"[USECASE DISPATCHER] ====================================================")
    print(f"[USECASE DISPATCHER] Camera ID: {camera_id}")
    
    # Query database for enabled usecases for this camera
    print(f"[USECASE DISPATCHER] Querying database for enabled usecases...")
    usecase_configs = get_enabled_usecases(camera_id)
    
    if not usecase_configs:
        print(f"[USECASE DISPATCHER] No enabled usecases found for camera '{camera_id}'")
        print(f"[USECASE DISPATCHER] Returning empty result set")
        print(f"[USECASE DISPATCHER] ====================================================\n")
        return {
            "camera_id": camera_id,
            "results": []
        }
    
    print(f"[USECASE DISPATCHER] Found {len(usecase_configs)} enabled usecase(s):")
    for config in usecase_configs:
        print(f"[USECASE DISPATCHER]   - {config['usecase_name']}")
    
    detections = detection_output.get("detections", [])
    screenshot_path = detection_output.get("screenshot_path")
    first_detection_id = detection_output.get("first_detection_id")
    timestamp = detection_output.get("timestamp")
    frame_id = detection_output.get("frame_id")
    print(f"[USECASE DISPATCHER] Detection output: {len(detections)} detections")
    print(f"[USECASE DISPATCHER] Screenshot: {screenshot_path}")
    print(f"[USECASE DISPATCHER] First detection ID: {first_detection_id}")
    print(f"[USECASE DISPATCHER] Timestamp: {timestamp}")
    print(f"[USECASE DISPATCHER] Frame ID: {frame_id}")
    print(f"[USECASE DISPATCHER] ====================================================\n")
    
    results = []
    
    for idx, config in enumerate(usecase_configs):
        usecase_name = config['usecase_name']
        roi = config.get('roi')
        print(f"[USECASE DISPATCHER] --- Evaluating Usecase {idx+1}/{len(usecase_configs)}: '{usecase_name}' ---")
        print(f"[USECASE DISPATCHER] ROI from DB: {roi}")
        
        try:
            # Get rule handler for this usecase (with ROI from database)
            rule = get_usecase_rule(usecase_name, roi)
            print(f"[USECASE DISPATCHER] Rule handler loaded: {rule.__class__.__name__}")
            
            # Evaluate the rule
            print(f"[USECASE DISPATCHER] Calling rule.evaluate()...")
            evaluation_result = rule.evaluate(detection_output)
            
            # Build result object
            result = UsecaseResult(
                usecase_id=usecase_name,
                triggered=evaluation_result["triggered"],
                matched_count=len(evaluation_result["matched_objects"]),
                matched_objects=evaluation_result["matched_objects"],
                detection_id=first_detection_id,
                screenshot_path=screenshot_path,
                timestamp=timestamp,
                frame_id=frame_id,
                metadata=evaluation_result.get("metadata", {})
            )
            
            print(f"[USECASE DISPATCHER] Usecase '{usecase_name}' result:")
            print(f"[USECASE DISPATCHER]   - Triggered: {result.triggered}")
            print(f"[USECASE DISPATCHER]   - Matched count: {result.matched_count}")
            
            results.append(result)
            
            # Persist result to database
            try:
                persist_usecase_result(
                    camera_id=camera_id,
                    usecase_name=usecase_name,
                    triggered=result.triggered,
                    detection_id=first_detection_id,
                    frame_id=frame_id,
                    metadata=result.metadata
                )
            except Exception as e:
                print(f"[USECASE DISPATCHER] DB persistence error: {str(e)}")
            
        except ValueError as e:
            print(f"[USECASE DISPATCHER] ERROR: {str(e)}")
            print(f"[USECASE DISPATCHER] Skipping unknown usecase '{usecase_name}'")
            continue
        except Exception as e:
            print(f"[USECASE DISPATCHER] ERROR: Usecase '{usecase_name}' evaluation failed: {str(e)}")
            print(f"[USECASE DISPATCHER] Skipping failed usecase")
            continue
    
    print(f"\n[USECASE DISPATCHER] ====================================================")
    print(f"[USECASE DISPATCHER] EVALUATION COMPLETE")
    print(f"[USECASE DISPATCHER] Total results: {len(results)}/{len(usecase_configs)}")
    
    triggered_count = sum(1 for r in results if r.triggered)
    print(f"[USECASE DISPATCHER] Triggered usecases: {triggered_count}")
    
    for result in results:
        status = "✓ TRIGGERED" if result.triggered else "✗ Not triggered"
        print(f"[USECASE DISPATCHER]   - {result.usecase_id}: {status} ({result.matched_count} matches)")
    
    print(f"[USECASE DISPATCHER] ====================================================\n")
    
    return {
        "camera_id": camera_id,
        "results": results
    }
