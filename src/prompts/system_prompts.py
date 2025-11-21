"""System prompts for maintenance triage agent."""

MAINTENANCE_TRIAGE_PROMPT = """
You are a maintenance triage assistant that coordinates with vendor services.

You MUST follow this protocol:

1. Read the tenant's title and description.

2. Determine the severity and whether the issue can be safely resolved via self-help:
   - SAFE for self-help: Minor leaks, clogged drains, tripped breakers, dirty filters
   - UNSAFE for self-help: Gas leaks, electrical sparks, major flooding, no heat/AC in extreme weather

3. For SAFE self-help issues:
   - You MUST call the `lookup_troubleshooting_article` tool with title and description
   - If the tool returns steps, use ONLY those to populate `self_help_steps`, `kb_article_id`, and `kb_article_title`
   - If the tool does NOT return an article (kb_article_id is null), generate safe, reasonable self-help steps based on your knowledge
   - Set `triage_label` to "SELF_HELP_OK"
   - Prioritize KB article steps when available; only generate your own when no article is found

4. For UNSAFE or emergency issues:
   - Set `triage_label` to "EMERGENCY" for immediate safety threats (gas, fire, electrical hazards)
   - Set `triage_label` to "VENDOR_REQUIRED" for issues requiring professional service
   - Set `self_help_steps` to []
   - You MUST call the `select_best_vendor` tool with:
     * issue_type: ELECTRICAL, PLUMBING, HVAC, GAS, or APPLIANCE
     * property_zip: the property ZIP code from the request
     * severity: LOW, MEDIUM, HIGH, or CRITICAL
   - Use ONLY the tool's returned vendor_id, vendor_name, service_type, and explanation
   - DO NOT invent vendor information - use only what the tool returns
   - If the tool returns vendor_id=null, set vendor_selection to null

5. For vendor operations (after vendor selection):
   - Use the `vendor_service_agent` sub-agent for:
     * Requesting quotes: Pass service_type, issue_description, property_zip, severity
     * Checking availability: Pass service_type, quote_id
     * Booking appointments: Pass quote_id, slot_id, tenant_name, tenant_phone
   - The vendor_service_agent will handle all vendor communication via A2A protocol

Return JSON ONLY in this exact schema:

```json
{
  "triage_label": "SELF_HELP_OK" | "VENDOR_REQUIRED" | "EMERGENCY",
  "explanation": "string",
  "self_help_steps": ["string"],
  "kb_article_id": "string or null",
  "kb_article_title": "string or null",
  "vendor_selection": {
    "vendor_id": "string or null",
    "vendor_name": "string or null",
    "service_type": "string or null",
    "explanation": "string"
  }
}
```

For subsequent vendor operations (quote, availability, booking), delegate to vendor_service_agent sub-agent.
"""


def format_triage_request(
    property_id: str,
    priority: str,
    title: str,
    description: str,
    property_zip: str = "unknown"
) -> str:
    """
    Format a maintenance request into a prompt for the triage agent.
    
    Args:
        property_id: ID of the property
        priority: Current priority level
        title: Issue title
        description: Detailed description
        property_zip: Property ZIP code for vendor selection
        
    Returns:
        Formatted prompt string
    """
    return f"""
Tenant maintenance request:

Property ID: {property_id}
Property ZIP: {property_zip}
Current priority: {priority}
Title: {title}
Description: {description}

Follow your JSON response schema exactly.
Remember: You MUST call the appropriate tools (lookup_troubleshooting_article or select_best_vendor) and use their output.
"""


def format_vendor_quote_request(
    service_type: str,
    issue_description: str,
    property_zip: str,
    severity: str
) -> str:
    """Format a vendor quote request."""
    return f"""
Please request a quote from the vendor with these details:
- Service type: {service_type}
- Issue description: {issue_description}
- Property ZIP: {property_zip}
- Severity: {severity}

Use the vendor_service_agent to get the quote.

Return JSON ONLY in this exact schema. Your output MUST be valid JSON and match this format exactly:

{{
  "quote_id": "string",
  "service_type": "string",
  "estimate": {{
    "labor": float,
    "parts": float,
    "travel": float,
    "total_estimate": float
  }},
  "valid_until": "string",
  "conditions": ["string"],
  "response_time": "string"
}}
"""


def format_vendor_availability_request(
    service_type: str,
    quote_id: str
) -> str:
    """Format a vendor availability check request."""
    return f"""
Please check availability from the vendor with these details:
- Service type: {service_type}
- Quote ID: {quote_id}

Use the vendor_service_agent to get available time slots.

Return JSON ONLY in this exact schema. Your output MUST be valid JSON and match this format exactly:

{{
  "quote_id": "string",
  "service_type": "string",
  "options": [
    {{
      "date": "string",
      "from": "string",
      "to": "string",
      "slot_id": "string"
    }}
  ],
  "booking_deadline": "string"
}}
"""


def format_vendor_booking_request(
    quote_id: str,
    slot_id: str,
    tenant_name: str,
    tenant_phone: str,
    special_instructions: str = ""
) -> str:
    """Format a vendor booking request."""
    instructions_text = f"\n- Special instructions: {special_instructions}" if special_instructions else ""
    return f"""
Please book an appointment with the vendor with these details:
- Quote ID: {quote_id}
- Slot ID: {slot_id}
- Tenant name: {tenant_name}
- Tenant phone: {tenant_phone}{instructions_text}

Use the vendor_service_agent to complete the booking.

Return JSON ONLY in this exact schema. Your output MUST be valid JSON and match this format exactly:

{{
  "booking_id": "string",
  "quote_id": "string",
  "slot_id": "string",
  "status": "string",
  "technician": {{
    "name": "string",
    "phone": "string",
    "rating": float
  }},
  "tenant_contact": {{
    "name": "string",
    "phone": "string"
  }},
  "special_instructions": "string",
  "confirmation_code": "string",
  "estimated_duration": "string"
}}
"""