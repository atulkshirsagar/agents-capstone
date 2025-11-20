"""Vendor selection tools for maintenance escalation."""

from typing import Dict, List
import pandas as pd
from src.data.vendors import vendors_df


def select_best_vendor(
    issue_type: str,
    property_zip: str,
    severity: str = "MEDIUM",
) -> Dict:
    """
    Select the best vendor for a maintenance issue based on issue type, location, and severity.
    
    This tool filters available vendors by service type and location, then ranks them
    based on rating, response speed, and pricing to recommend the most suitable vendor.
    
    Args:
        issue_type: Type of maintenance issue (ELECTRICAL, PLUMBING, HVAC, GAS, APPLIANCE)
        property_zip: ZIP code of the property requiring service
        severity: Severity level of the issue (LOW, MEDIUM, HIGH, CRITICAL). Default is MEDIUM.
        
    Returns:
        dict with keys:
            - vendor_id: Selected vendor's ID
            - vendor_name: Selected vendor's name
            - service_type: Type of service they provide
            - rating: Vendor's rating (0-5)
            - estimated_response_time: How quickly they can respond
            - price_band: Relative pricing (1=budget, 2=standard, 3=premium)
            - explanation: Why this vendor was selected
            
        If no suitable vendor found, returns vendor_id=None with explanation.
    """
    print(f"[VENDOR_TOOL] select_best_vendor called: issue_type='{issue_type}', property_zip='{property_zip}', severity='{severity}'")
    
    # Map issue types to service types
    ISSUE_TO_SERVICE_TYPE = {
        "ELECTRICAL": "ELECTRICIAN",
        "APPLIANCE": "APPLIANCE_REPAIR",
        "PLUMBING": "PLUMBER",
        "GAS": "GAS_TECHNICIAN",
        "HVAC": "HVAC",
        "OTHER": None,
    }
    
    service_type = ISSUE_TO_SERVICE_TYPE.get(issue_type.upper())
    
    if service_type is None:
        print(f"[VENDOR_TOOL] No matching service type for issue_type: {issue_type}")
        return {
            "vendor_id": None,
            "vendor_name": None,
            "service_type": None,
            "rating": None,
            "estimated_response_time": None,
            "price_band": None,
            "explanation": f"No matching service type found for issue type '{issue_type}'."
        }
    
    # Filter vendors by service type
    candidates = vendors_df[vendors_df["service_type"] == service_type].copy()
    
    if candidates.empty:
        print(f"[VENDOR_TOOL] No vendors found for service_type: {service_type}")
        return {
            "vendor_id": None,
            "vendor_name": None,
            "service_type": service_type,
            "rating": None,
            "estimated_response_time": None,
            "price_band": None,
            "explanation": f"No vendors available for {service_type} service."
        }
    
    # Convert property_zip to int for comparison
    try:
        prop_zip_int = int(property_zip)
    except (ValueError, TypeError):
        prop_zip_int = 0
    
    # Prioritize vendors in the same ZIP code
    candidates["zip_match"] = (candidates["zip"].astype(int) == prop_zip_int).astype(int)
    
    # Calculate utility score: higher rating, faster speed, lower price is better
    # For critical issues, prioritize speed over price
    if severity.upper() == "CRITICAL":
        candidates["utility_score"] = (
            2.5 * candidates["rating"] + 
            2.0 * candidates["speed_score"] - 
            0.5 * candidates["price_band"]
        )
    else:
        candidates["utility_score"] = (
            2.0 * candidates["rating"] + 
            1.5 * candidates["speed_score"] - 
            1.0 * candidates["price_band"]
        )
    
    # Sort by ZIP match first, then utility score
    candidates_sorted = candidates.sort_values(
        by=["zip_match", "utility_score"], 
        ascending=[False, False]
    )
    
    # Select the best vendor
    best = candidates_sorted.iloc[0]
    
    # Build explanation
    zip_note = "in your area" if best["zip_match"] == 1 else f"near ZIP {property_zip}"
    explanation = (
        f"Selected {best['name']} for {service_type} service {zip_note}. "
        f"They have a {best['rating']:.1f}/5.0 rating, "
        f"{'fast' if best['speed_score'] >= 4 else 'standard'} response time, "
        f"and {'budget-friendly' if best['price_band'] == 1 else 'competitive'} pricing."
    )
    
    print(f"[VENDOR_TOOL] Selected vendor: {best['vendor_id']} - {best['name']}")
    
    return {
        "vendor_id": best["vendor_id"],
        "vendor_name": best["name"],
        "service_type": service_type,
        "rating": float(best["rating"]),
        "estimated_response_time": f"{int(best['speed_score'])} hours" if best['speed_score'] < 24 else f"{int(best['speed_score']/24)} days",
        "price_band": int(best["price_band"]),
        "explanation": explanation,
    }