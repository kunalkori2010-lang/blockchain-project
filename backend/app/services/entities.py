import json
import os

_CACHE = None


def load_entities() -> list[dict]:
    global _CACHE
    if _CACHE is None:
        p = os.path.join(os.path.dirname(__file__), "known_entities.json")
        with open(p, "r", encoding="utf-8") as f:
            _CACHE = json.load(f)
    return _CACHE


def entity_map() -> dict:
    return {e["address"].lower(): e for e in load_entities()}
