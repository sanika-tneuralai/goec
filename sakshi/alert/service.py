"""
Alert service for processing and sending alerts.
"""
from alert.schemas import AlertRequest, AlertResponse


def process_alert(request: AlertRequest) -> AlertResponse:
    """
    Process alert request and determine if alert should be sent.
    
    Alert Rule:
    - Send alert if usecase_id == "person_in_roi" AND alert_required == true
    """
    print(f"\n[SERVICE] ============== FUNCTION ENTRY: process_alert ==============")
    print(f"[SERVICE] Payload received: camera_id={request.camera_id}, usecase_id={request.usecase_id}, alert_required={request.alert_required}")
    
    # Evaluate alert rule
    print(f"[SERVICE] Evaluating alert rule...")
    print(f"[SERVICE] Condition check: usecase_id == 'person_in_roi' AND alert_required == true")
    print(f"[SERVICE] usecase_id: {request.usecase_id} == 'person_in_roi': {request.usecase_id == 'person_in_roi'}")
    print(f"[SERVICE] alert_required: {request.alert_required}")
    
    alert_sent = False
    message = ""
    
    if request.usecase_id == "person_in_roi" and request.alert_required:
        # Alert rule matched - simulate sending alert
        print(f"\n[ALERT] ⚠️  ALERT TRIGGERED ⚠️")
        print(f"[ALERT] Camera: {request.camera_id}")
        print(f"[ALERT] Type: {request.alert_type}")
        print(f"[ALERT] Objects detected: {request.alert_count}")
        
        alert_sent = True
        message = "Person detected inside ROI. Alert sent."
        print(f"[SERVICE] Alert sent successfully")
    else:
        message = "Alert conditions not met. No alert sent."
        print(f"[SERVICE] Alert rule not matched - no alert sent")
    
    response = AlertResponse(
        camera_id=request.camera_id,
        alert_sent=alert_sent,
        alert_type=request.alert_type,
        alert_count=request.alert_count,
        message=message
    )
    
    print(f"[SERVICE] Returning response: alert_sent={response.alert_sent}, message={response.message}")
    print(f"[SERVICE] ============== FUNCTION EXIT: process_alert ==============\n")
    
    return response
