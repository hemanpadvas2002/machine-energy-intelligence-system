import pandas as pd
import streamlit as st

from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar


apply_page_config("AMTDC Logs")
inject_styles()
render_sidebar("Logs")
render_shell("System Logs", "Active Stream", "System Telemetry", "Logs")

logs = pd.DataFrame(
    [
        ["2026-03-26 14:02:44", "ERROR", "CNC-X42-M4", "Critical spindle overheat. Automatic shutdown triggered."],
        ["2026-03-26 14:01:13", "WARNING", "ARM-ROB-09", "Hydraulic pressure drop detected in secondary line."],
        ["2026-03-26 13:58:04", "INFO", "LSR-CUT-01", "Routine maintenance cycle completed. Optics calibrated."],
        ["2026-03-26 13:55:22", "INFO", "CNC-X42-M1", "Batch job 8821 started successfully."],
        ["2026-03-26 13:50:12", "ERROR", "PLC-CON-04", "Communication timeout with peripheral node P04."],
        ["2026-03-26 13:48:44", "WARNING", "ARM-ROB-12", "Predictive maintenance alert: end-effector wear nearing threshold."],
    ],
    columns=["Timestamp", "Event Type", "Machine ID", "Detailed Message"],
)

top_cols = st.columns([2, 1], gap="large")
with top_cols[0]:
    search = st.text_input("Search Machine ID or Message", placeholder="Search machine ID or message...")
with top_cols[1]:
    st.date_input("Today", label_visibility="collapsed")

filtered = logs.copy()
if search:
    mask = filtered.apply(lambda col: col.astype(str).str.contains(search, case=False, na=False))
    filtered = filtered[mask.any(axis=1)]

st.dataframe(filtered, use_container_width=True, hide_index=True)

metric_cols = st.columns(3)
metric_cols[0].markdown(
    """
    <div class="section-card" style="border-left:4px solid #cf2e2e;">
        <div class="soft-label">Errors (24h)</div>
        <div class="metric-value" style="margin-top:0.6rem;">12</div>
    </div>
    """,
    unsafe_allow_html=True,
)
metric_cols[1].markdown(
    """
    <div class="section-card" style="border-left:4px solid #a47400;">
        <div class="soft-label">Warnings (24h)</div>
        <div class="metric-value" style="margin-top:0.6rem;">84</div>
    </div>
    """,
    unsafe_allow_html=True,
)
metric_cols[2].markdown(
    """
    <div class="section-card" style="background:#d9edf8;">
        <div class="soft-label">System Load</div>
        <div class="metric-value" style="margin-top:0.6rem;">28.4%</div>
    </div>
    """,
    unsafe_allow_html=True,
)

close_shell()
