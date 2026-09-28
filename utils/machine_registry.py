import json
import os

from config.settings import MACHINE_TABLE_MAPPING

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "machines_config.json")


def get_all_machines() -> dict:
    """Return MACHINE_TABLE_MAPPING merged with any machines added via the Add Machine page."""
    merged = dict(MACHINE_TABLE_MAPPING)
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for name, meta in data.items():
            if name.startswith("_"):
                continue
            if name not in merged and isinstance(meta, dict) and meta.get("ip"):
                table = name.lower().replace(" ", "_").replace("-", "_")
                merged[name] = table
    except Exception:
        pass
    return merged
