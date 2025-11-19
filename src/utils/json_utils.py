import json

def extract_json_from_llm_output(text: str):
    """
    Cleans LLM output and parses JSON, removing code block markers if present.
    Returns parsed dict or raises JSONDecodeError.
    """
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
    return json.loads(cleaned)