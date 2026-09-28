import ipaddress
import json
import os

import streamlit as st

from config.settings import MACHINE_TABLE_MAPPING
from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar

apply_page_config("AMTDC Add Machine")
inject_styles()
render_sidebar("Add Machine")
render_shell("Registration", "System Entry", "Equipment Console", "Add Machine")

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "machines_config.json")


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}


def _save_machine(name: str, meta: dict) -> None:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"_note": "Runtime-editable machine metadata. IP/port are managed in config/settings.py DEVICES."}
    data[name] = meta
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _validate_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip.strip())
        return True
    except ValueError:
        return False


left_col, right_col = st.columns([1.8, 1], gap="large")

with left_col:
    st.markdown(
        """
        <div class="section-card">
            <div class="soft-label">System Entry</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2.2rem;margin:0.35rem 0 1.2rem 0;">Equipment Parameters</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("add_machine_form"):
        first_row = st.columns(2)
        machine_name = first_row[0].text_input("Machine Name", placeholder="e.g. Galaxy_CNC_2")
        machine_type = first_row[1].selectbox(
            "Equipment Type",
            ["CNC Machine", "Industrial Compressor", "HVAC System", "Hydraulic Press", "Robotic Arm"],
        )

        second_row = st.columns(2)
        ip_address = second_row[0].text_input("IP Address", placeholder="e.g. 192.168.1.100")
        port = second_row[1].number_input("Modbus Port", min_value=1, max_value=65535, value=502, step=1)

        third_row = st.columns(2)
        location = third_row[0].text_input("Facility Location", placeholder="Sector 7, Bay 4")
        description = third_row[1].text_input("Description", placeholder="Short label for this machine")

        submitted = st.form_submit_button("Save Machine", use_container_width=True)

    if submitted:
        errors = []
        name_clean = machine_name.strip()
        ip_clean = ip_address.strip()

        if not name_clean:
            errors.append("Machine Name is required.")
        if not ip_clean or not _validate_ip(ip_clean):
            errors.append(f"'{ip_clean}' is not a valid IP address.")

        if name_clean:
            existing = _load_config()
            if name_clean in MACHINE_TABLE_MAPPING or name_clean in existing:
                errors.append(f"Machine '{name_clean}' is already registered.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            _save_machine(name_clean, {
                "ip": ip_clean,
                "port": int(port),
                "type": machine_type,
                "location": location.strip(),
                "description": description.strip(),
                "notes": "",
            })
            st.success(
                f"Machine **{name_clean}** registered as {machine_type}. "
                "It will appear in dropdowns on next page load."
            )

with right_col:
    st.markdown(
        """
        <div class="hero-band">
            <h3>Registry Guidelines</h3>
            <p style="margin:1rem 0 0 0;color:#d9f6f6;line-height:1.7;">
                Ensure all precision assets are registered with unique identifiers.
                IP address and port must match the machine's Modbus TCP configuration.
            </p>
            <div style="margin-top:2rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,0.2);display:flex;justify-content:space-between;">
                <span class="soft-label" style="color:#c7f1f1;">Global Tolerance</span>
                <strong style="font-size:2rem;">+- 0.002%</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="section-card" style="margin-top:1.5rem;">
            <div class="soft-label">Live Calibration</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.35rem 0 0.7rem 0;">Digital Twin Ready</h3>
            <p style="color:#61748d;line-height:1.7;margin:0;">
                Adding equipment automatically initializes a digital twin profile for telemetry baselining and stress simulation.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

footer_cols = st.columns(3)
footer_cols[0].markdown("**Database Node**  \nAMT-DB-NORTH-01")
footer_cols[1].markdown("**Status**  \nCONNECTED")
footer_cols[2].markdown("**Snapshot**  \nRegistration UI active")

close_shell()
