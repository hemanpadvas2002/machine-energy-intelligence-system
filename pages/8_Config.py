import json
import os
import time

import streamlit as st

from config.settings import DEVICES, MACHINE_TABLE_MAPPING
from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar

apply_page_config("AMTDC Config")
inject_styles()
render_sidebar("Config")
render_shell("Config", "System", "Machine Configuration", "Config")

MACHINES_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "machines_config.json")
_CONFIG_TTL = 30
_config_cache: dict = {}
_config_loaded_at: float = 0.0


def _load_config() -> dict:
    global _config_cache, _config_loaded_at
    if time.time() - _config_loaded_at < _CONFIG_TTL and _config_cache:
        return _config_cache
    try:
        with open(MACHINES_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _config_cache = {k: v for k, v in data.items() if not k.startswith("_")}
        _config_loaded_at = time.time()
        return _config_cache
    except Exception:
        return {}


def _save_config(config: dict) -> None:
    global _config_cache, _config_loaded_at
    payload = {"_note": "Runtime-editable machine metadata. IP/port are managed in config/settings.py DEVICES."}
    payload.update(config)
    with open(MACHINES_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    _config_cache = config.copy()
    _config_loaded_at = time.time()


# Build lookup: machine name → DEVICES entry (for IP/port reference)
_devices_map = {d["name"]: d for d in DEVICES}

config = _load_config()

# Ensure every known machine has an entry
for name in MACHINE_TABLE_MAPPING:
    if name not in config:
        config[name] = {"description": "", "notes": ""}

st.markdown("### Registered Machines")
st.caption("Edit descriptions and notes below. IP and port are read-only — change them in `config/settings.py`.")

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

changes: dict = {}

for machine_name in list(MACHINE_TABLE_MAPPING.keys()):
    device = _devices_map.get(machine_name, {})
    ip = device.get("host", "—")
    port = device.get("port", "—")
    table = MACHINE_TABLE_MAPPING[machine_name]
    meta = config.get(machine_name, {"description": "", "notes": ""})

    with st.container():
        st.markdown(
            f"""
            <div class="panel" style="margin-bottom:18px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
                <div>
                  <div class="section-label">Machine</div>
                  <div style="font-size:18px;font-weight:700;margin-top:4px">{machine_name.replace("_", " ")}</div>
                </div>
                <div style="text-align:right">
                  <div class="section-label">Connection</div>
                  <div style="font-size:13px;color:#526273;margin-top:4px">{ip} &nbsp;·&nbsp; port&nbsp;{port}</div>
                  <div style="font-size:11px;color:#8ba0b8;margin-top:2px">table: {table}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_desc, col_notes = st.columns([2, 3])
        with col_desc:
            new_desc = st.text_input(
                "Description",
                value=meta.get("description", ""),
                key=f"cfg_desc_{machine_name}",
                placeholder="Short label for this machine",
            )
        with col_notes:
            new_notes = st.text_input(
                "Notes",
                value=meta.get("notes", ""),
                key=f"cfg_notes_{machine_name}",
                placeholder="Optional notes (calibration date, location, etc.)",
            )
        changes[machine_name] = {"description": new_desc, "notes": new_notes}

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

save_col, _ = st.columns([1, 5])
with save_col:
    if st.button("Save Changes", type="primary", use_container_width=True):
        _save_config(changes)
        st.success("Configuration saved.")
        st.rerun()

close_shell()
