"""Vendor service tools for maintenance operations."""

from typing import Dict, Any
from datetime import datetime, timedelta
import random


def request_quote(
    service_type: str,
    issue_description: str,
    property_zip: str,
    severity: str = "MEDIUM"
) -> Dict[str, Any]:
    """
    Generate a quote for maintenance service.
    
    Args:
        service_type: Type of service (HVAC, PLUMBING, ELECTRICAL, etc.)
        issue_description: Description of the maintenance issue
        property_zip: Property ZIP code
        severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
        
    Returns:
        Quote information including estimate and validity
    """
    print(f"[VENDOR_TOOL] request_quote called: service_type='{service_type}', severity='{severity}'")
    
    # Base prices by service type
    base_prices = {
        "HVAC": 250,
        "PLUMBING": 150,
        "ELECTRICAL": 200,
        "GAS": 300,
        "APPLIANCE": 120,
    }
    
    # Severity multipliers
    severity_multipliers = {
        "LOW": 0.8,
        "MEDIUM": 1.0,
        "HIGH": 1.3,
        "CRITICAL": 1.8,
    }
    
    base = base_prices.get(service_type, 180)
    multiplier = severity_multipliers.get(severity.upper(), 1.0)
    total = base * multiplier
    
    # Add some randomness
    total = total + random.randint(-20, 50)
    
    quote_id = f"Q-{service_type[:4]}-{random.randint(1000, 9999)}"
    valid_until = (datetime.now() + timedelta(days=7)).isoformat()
    
    return {
        "quote_id": quote_id,
        "service_type": service_type,
        "estimate": {
            "labor": round(total * 0.6, 2),
            "parts": round(total * 0.3, 2),
            "travel": round(total * 0.1, 2),
            "total_estimate": round(total, 2),
        },
        "valid_until": valid_until,
        "conditions": [
            "Estimate may change based on inspection",
            "Parts availability not guaranteed",
            "Standard warranty applies"
        ],
        "response_time": "Same day" if severity == "CRITICAL" else "1-2 business days"
    }


def get_availability(
    service_type: str,
    quote_id: str,
    preferred_date: str = None
) -> Dict[str, Any]:
    """
    Get available time slots for service.
    
    Args:
        service_type: Type of service
        quote_id: Quote ID from request_quote
        preferred_date: Optional preferred date (YYYY-MM-DD)
        
    Returns:
        Available time slots
    """
    print(f"[VENDOR_TOOL] get_availability called: service_type='{service_type}', quote_id='{quote_id}'")
    
    # Generate next 5 available slots
    start_date = datetime.now() + timedelta(days=1)
    slots = []
    
    for i in range(5):
        date = start_date + timedelta(days=i)
        slots.append({
            "date": date.strftime("%Y-%m-%d"),
            "from": "09:00",
            "to": "12:00",
            "slot_id": f"SLOT-{date.strftime('%Y%m%d')}-AM"
        })
        slots.append({
            "date": date.strftime("%Y-%m-%d"),
            "from": "13:00",
            "to": "17:00",
            "slot_id": f"SLOT-{date.strftime('%Y%m%d')}-PM"
        })
    
    return {
        "quote_id": quote_id,
        "service_type": service_type,
        "options": slots[:5],  # Return first 5 slots
        "booking_deadline": (datetime.now() + timedelta(hours=48)).isoformat()
    }


def book_slot(
    quote_id: str,
    slot_id: str,
    tenant_name: str,
    tenant_phone: str,
    special_instructions: str = ""
) -> Dict[str, Any]:
    """
    Book a service appointment.
    
    Args:
        quote_id: Quote ID from request_quote
        slot_id: Slot ID from get_availability
        tenant_name: Tenant contact name
        tenant_phone: Tenant contact phone
        special_instructions: Optional special instructions
        
    Returns:
        Booking confirmation
    """
    print(f"[VENDOR_TOOL] book_slot called: quote_id='{quote_id}', slot_id='{slot_id}'")
    
    booking_id = f"BK-{random.randint(10000, 99999)}"
    
    return {
        "booking_id": booking_id,
        "quote_id": quote_id,
        "slot_id": slot_id,
        "status": "CONFIRMED",
        "technician": {
            "name": random.choice(["Mike Johnson", "Sarah Chen", "David Martinez", "Lisa Anderson"]),
            "phone": "555-0100",
            "rating": round(random.uniform(4.5, 5.0), 1)
        },
        "tenant_contact": {
            "name": tenant_name,
            "phone": tenant_phone
        },
        "special_instructions": special_instructions,
        "confirmation_code": f"CONF-{random.randint(100000, 999999)}",
        "estimated_duration": "2-4 hours"
    }