import json
import os

import streamlit as st

from config.settings import DEVICES, DEFAULT_IDLE_THRESHOLD_KW, DEFAULT_WORKING_THRESHOLD_KW
from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar

_THRESHOLDS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "config", "thresholds.json")
)


def _load_thresholds() -> dict:
    try:
        with open(_THRESHOLDS_PATH, "r") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}


def _save_thresholds(thresholds: dict) -> bool:
    try:
        existing: dict = {}
        try:
            with open(_THRESHOLDS_PATH, "r") as f:
                existing = json.load(f)
        except Exception:
            pass
        # Preserve metadata keys, overwrite machine entries
        meta = {k: v for k, v in existing.items() if k.startswith("_")}
        meta.update(thresholds)
        with open(_THRESHOLDS_PATH, "w") as f:
            json.dump(meta, f, indent=2)
        return True
    except Exception as exc:
        st.error(f"Could not save thresholds.json: {exc}")
        return False


apply_page_config("AMTDC Settings")
inject_styles()
render_sidebar("Settings")
render_shell("System Settings", "Configuration", "Configuration Console", "Settings")

left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    st.markdown(
        """
        <div class="section-card">
            <div class="soft-label">User Profile</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.6rem 0 0.35rem 0;">Marcus Vance</h3>
            <p style="margin:0;color:#61748d;">Senior Systems Engineer</p>
            <div style="margin-top:1.8rem;">
                <div class="soft-label">Email Address</div>
                <p style="font-size:1.2rem;margin:0.6rem 0 1.2rem 0;">m.vance@amtdc.industrial</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("Edit Profile", use_container_width=True)

    st.markdown(
        """
        <div class="section-card" style="margin-top:1.5rem;">
            <div class="soft-label">Interface Theme</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:1.7rem;margin:0.6rem 0 1rem 0;">Light Graphite</h3>
            <p style="margin:0;color:#61748d;">The current UI follows the light industrial shell you attached.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right_col:
    st.markdown(
        """
        <div class="section-card">
            <div class="soft-label">Telemetry Tolerances</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2.3rem;margin:0.35rem 0 0.4rem 0;">Machine Power Thresholds</h3>
            <p style="margin:0 0 1rem 0;color:#61748d;font-size:0.92rem;">
                kW &lt; <b>IDLE</b> threshold → IDLE &nbsp;|&nbsp;
                kW &gt; <b>WORKING</b> threshold → WORKING &nbsp;|&nbsp;
                between → TRANSITION.<br>
                Changes take effect within 30 s — no restart required.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    current = _load_thresholds()
    machine_names = [d["name"] for d in DEVICES]
    new_thresholds: dict = {}
    with st.form("threshold_form"):
        for name in machine_names:
            saved = current.get(name, {})
            idle_val  = float(saved.get("idle_threshold_kw",  DEFAULT_IDLE_THRESHOLD_KW))
            work_val  = float(saved.get("working_threshold_kw", DEFAULT_WORKING_THRESHOLD_KW))
            st.markdown(f"**{name.replace('_', ' ')}**")
            cols = st.columns(2)
            new_idle = cols[0].number_input(
                "IDLE threshold (kW)",
                min_value=0.0, max_value=500.0,
                value=idle_val, step=0.01, format="%.3f",
                key=f"idle_{name}",
            )
            new_work = cols[1].number_input(
                "WORKING threshold (kW)",
                min_value=0.0, max_value=500.0,
                value=work_val, step=0.01, format="%.3f",
                key=f"work_{name}",
            )
            new_thresholds[name] = {
                "idle_threshold_kw": round(new_idle, 3),
                "working_threshold_kw": round(new_work, 3),
            }
        if st.form_submit_button("Save Thresholds", use_container_width=True):
            if _save_thresholds(new_thresholds):
                st.success("Saved — fetcher will pick up changes within 30 s.")
    st.caption(
        "⚠ All 4 machines are using the global default (2.82 / 3.05 kW). "
        "Calibrate once live working-load readings are available for each unit."
    )

    bottom_cols = st.columns(2, gap="large")
    with bottom_cols[0]:
        st.markdown(
            """
            <div class="section-card">
                <div class="soft-label">Dispatch Rules</div>
                <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.35rem 0 1rem 0;">Notifications</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.toggle("Email Alerts", value=True)
        st.toggle("SMS Push", value=False)
    with bottom_cols[1]:
        st.markdown(
            """
            <div class="section-card">
                <div class="soft-label">External Integrations</div>
                <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.35rem 0 1rem 0;">API Keys</h3>
                <p style="color:#61748d;">Provision and manage access tokens for third-party telemetry software.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code("AK-882-XXXX-XXXX")
        action_cols = st.columns(2)
        action_cols[0].button("Revoke", use_container_width=True)
        action_cols[1].button("Generate New Key", use_container_width=True)

footer_cols = st.columns([1, 1, 1.2])
footer_cols[0].markdown("Last synced: Today, 08:42 AM")
footer_cols[1].button("Discard Changes", use_container_width=True)
footer_cols[2].button("Commit Configuration", use_container_width=True)

close_shell()
