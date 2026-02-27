"""
Usecase rules module.
"""
from usecase.rules.base import BaseUsecaseRule
from usecase.rules.person_in_roi import PersonInROIRule
from usecase.rules.crowd_in_roi import CrowdInROIRule
from usecase.rules.restricted_zone import RestrictedZoneRule
from usecase.rules.people_count import PeopleCountRule


# Registry of all available usecase rules
USECASE_REGISTRY = {
    "person_in_roi": PersonInROIRule,
    "crowd_in_roi": CrowdInROIRule,
    "restricted_zone_breach": RestrictedZoneRule,
    "people_count": PeopleCountRule,
}


def get_usecase_rule(usecase_id: str, roi: str = None) -> BaseUsecaseRule:
    """
    Get a usecase rule instance by ID.
    
    Args:
        usecase_id: Usecase identifier
        roi: ROI configuration from database (JSON string or None)
        
    Returns:
        Usecase rule instance
        
    Raises:
        ValueError: If usecase_id is not registered
    """
    print(f"[REGISTRY] Looking up usecase: {usecase_id}")
    
    if usecase_id not in USECASE_REGISTRY:
        available = ", ".join(USECASE_REGISTRY.keys())
        print(f"[REGISTRY] ERROR: Usecase '{usecase_id}' not found")
        print(f"[REGISTRY] Available usecases: {available}")
        raise ValueError(f"Unknown usecase: {usecase_id}. Available: {available}")
    
    rule_class = USECASE_REGISTRY[usecase_id]
    print(f"[REGISTRY] Found rule class: {rule_class.__name__}")
    
    return rule_class(usecase_id, roi)
