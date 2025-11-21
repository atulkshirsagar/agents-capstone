"""Knowledge Base tools for maintenance troubleshooting."""

from typing import List, Dict

kb_articles = [
    {
        "id": "kb_hvac_01",
        "title": "AC not cooling",
        "keywords": ["ac", "air conditioner", "cooling", "not cold", "hvac"],
        "steps": [
            "Check if the thermostat is set to COOL and temperature lower than room temp.",
            "Ensure the filter is not clogged; clean or replace if dirty.",
            "Check if the outdoor unit is powered on and not blocked.",
        ],
    },
    {
        "id": "kb_leak_01",
        "title": "Minor sink leak under kitchen",
        "keywords": ["sink", "leak", "kitchen", "drip", "pipe"],
        "steps": [
            "Place a small bucket under the leak.",
            "Tighten the visible compression nut by hand if safe.",
            "Avoid using that sink until a plumber checks it.",
        ],
    },
    {
        "id": "kb_appliance_01",
        "title": "Washing machine not draining",
        "keywords": ["washer", "washing machine", "not draining", "drain"],
        "steps": [
            "Unplug the washing machine.",
            "Check and clean the lint filter/drain filter.",
            "Ensure the drain hose is not kinked or blocked.",
        ],
    },
    {
        "id": "kb_electrical_01",
        "title": "Tripped breaker or room lights not working",
        "keywords": [
            "breaker", "tripped", "lights not working", "bedroom lights", "power outage", "circuit", "electrical", "no power"
        ],
        "steps": [
            "Check your home's electrical panel for any breakers that are in the 'off' position.",
            "If you find a tripped breaker, flip it fully to the 'off' position, then back to 'on'.",
            "If the breaker trips again immediately, do not attempt further resets and contact maintenance.",
            "If power is restored, monitor for further issues."
        ],
    },
]


def _simple_kb_score(text: str, keywords: List[str]) -> int:
    """Calculate simple keyword match score."""
    text_l = text.lower()
    return sum(1 for kw in keywords if kw in text_l)


def lookup_troubleshooting_article(
    title: str,
    description: str,
) -> Dict:
    """
    Looks up a troubleshooting article from the maintenance KB.

    Args:
      title: Short problem title from the tenant.
      description: Longer free-text description.

    Returns:
      dict with keys: article_id, article_title, suggested_steps (List[str]).
      If no good match, returns an empty result with suggested_steps = [].
    """
    print(f"[KB_TOOL] lookup_troubleshooting_article called with title='{title}' description='{description}'")
    full_text = f"{title}\n{description}".lower()
    best = None
    best_score = 0
    
    for art in kb_articles:
        score = _simple_kb_score(full_text, art["keywords"])
        if score > best_score:
            best_score = score
            best = art

    if not best or best_score == 0:
        print("[KB_TOOL] No matching article found.")
        return {
            "article_id": None,
            "article_title": None,
            "suggested_steps": [],
        }

    print(f"[KB_TOOL] Matched article: {best['id']} - {best['title']}")
    return {
        "article_id": best["id"],
        "article_title": best["title"],
        "suggested_steps": best["steps"],
    }