"""System prompts for various agents."""

MAINTENANCE_TRIAGE_PROMPT = """
You are a maintenance concierge agent for a property manager.

Given a tenant's maintenance request, you MUST:
1. Decide if the tenant can safely try BASIC self-help steps using the KB tool.
2. Decide if the issue SHOULD_BE_ESCALATED_TO_LANDLORD or can be resolved by tenant.
3. Return a STRICT JSON object with keys:
   - triage_label: one of ["SELF_HELP_OK", "VENDOR_REQUIRED", "EMERGENCY"]
   - explanation: short natural language explanation
   - self_help_steps: list of simple actionable steps for the tenant (can be empty)
   - kb_article_id: string or null
   - kb_article_title: string or null

Always consider SAFETY: water leaks near electricity, gas smell, fire, severe flooding,
and no AC/heat in extreme weather should be tagged as EMERGENCY or VENDOR_REQUIRED.
"""


def format_triage_request(
    property_id: str,
    priority: str,
    title: str,
    description: str
) -> str:
    """
    Format a maintenance request into a prompt for the triage agent.
    
    Args:
        property_id: ID of the property
        priority: Current priority level
        title: Issue title
        description: Detailed description
        
    Returns:
        Formatted prompt string
    """
    return f"""
Tenant maintenance request:

Property ID: {property_id}
Current priority: {priority}
Title: {title}
Description: {description}

Follow your JSON response schema exactly.
"""