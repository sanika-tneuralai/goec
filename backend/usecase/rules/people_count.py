"""
People count usecase rule.

Rule: Count number of persons detected per frame.
This is an informational usecase (triggered = false) that provides metrics for analytics.
"""
from typing import Dict, Any
from usecase.rules.base import BaseUsecaseRule


class PeopleCountRule(BaseUsecaseRule):
    """
    Usecase: Count people detected in frame.
    
    This usecase does NOT trigger alerts. It provides metrics for analytics dashboards.
    Always returns triggered=False, but includes count in metadata.
    """
    
    def evaluate(self, detection_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Count persons detected in the frame.
        
        Args:
            detection_output: Detection API response
            
        Returns:
            Evaluation result with triggered=False and people count in metadata
        """
        print(f"\\n[RULE:{self.usecase_id}] ========== EVALUATION START ==========")
        
        detections = self.get_detections(detection_output)
        print(f"[RULE:{self.usecase_id}] Processing {len(detections)} detections")
        
        matched_objects = []
        people_count = 0
        
        for idx, detection in enumerate(detections):
            class_name = detection.get("class_name", "")
            confidence = detection.get("confidence", 0.0)
            
            print(f"[RULE:{self.usecase_id}] Detection {idx+1}: class='{class_name}', conf={confidence:.2f}")
            
            # Count all persons (regardless of ROI)
            if class_name == "person":
                people_count += 1
                print(f"[RULE:{self.usecase_id}] ✓ Person detected (confidence: {confidence:.2f})")
                matched_objects.append(detection)
        
        # This usecase is informational only - never triggers alerts
        triggered = False
        
        print(f"[RULE:{self.usecase_id}] Evaluation complete:")
        print(f"[RULE:{self.usecase_id}]   - Triggered: {triggered} (informational only)")
        print(f"[RULE:{self.usecase_id}]   - People count: {people_count}")
        print(f"[RULE:{self.usecase_id}] ========== EVALUATION END ==========\\n")
        
        return {
            "triggered": triggered,
            "matched_objects": matched_objects,
            "metadata": {
                "people_count": people_count,
                "rule_type": "informational"
            }
        }
