import sqlite3

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config.settings import ACTIVE_MACHINE_NAMES, DEVICES, MACHINE_TABLE_MAPPING, SQLITE_DB_PATH
from services.telemetry_runtime import ensure_telemetry_server_process
from services.telemetry_stream import STREAM_PORT
from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar
from ui.streaming_dashboard import build_streaming_dashboard_html
from utils.db_handler import fetch_latest_machine_snapshots
from utils.network import get_lan_ip


apply_page_config("AMTDC Dashboard")

_STATE_COLS = {
    "timestamp":   "Last Sync",
    "total_kw":    "Load (kW)",
    "state_label": "Operational State",
}


def _fetch_machine_states() -> pd.DataFrame:
    rows = []
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            for device in DEVICES:
                name = device["name"]
                table = MACHINE_TABLE_MAPPING.get(name)
                if not table:
                    continue
                try:
                    row = conn.execute(
                        f"SELECT timestamp, total_kw, state_label "
                        f"FROM {table} ORDER BY id DESC LIMIT 1"
                    ).fetchone()
                except Exception:
                    row = None
                if row:
                    ts, kw, state = row
                    rows.append({
                        "Machine ID":        name,
                        "Operational State": state or "—",
                        "Load (kW)":         round(float(kw or 0.0), 3),
                        "Last Sync":         ts[11:19] if ts and len(ts) >= 19 else ts or "—",
                    })
                else:
                    rows.append({
                        "Machine ID":        name,
                        "Operational State": "No data",
                        "Load (kW)":         0.0,
                        "Last Sync":         "—",
                    })
    except Exception:
        pass
    return pd.DataFrame(rows)


@st.fragment(run_every=3)
def _machine_state_panel() -> None:
    df = _fetch_machine_states()
    if df.empty:
        st.info("Waiting for machine data…")
        return
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Machine ID":        st.column_config.TextColumn("Machine ID",        width="medium"),
            "Operational State": st.column_config.TextColumn("Operational State", width="small"),
            "Load (kW)":         st.column_config.NumberColumn("Load (kW)",        format="%.3f", width="small"),
            "Last Sync":         st.column_config.TextColumn("Last Sync",          width="small"),
        },
    )


def main():
    ensure_telemetry_server_process()

    inject_styles()
    render_sidebar("Dashboard")
    render_shell("Telemetry Dashboard", "Live Data", "Digital Transformation Dashboard", "Dashboard")

    snapshots = {
        machine: row
        for machine, row in fetch_latest_machine_snapshots().items()
        if machine in ACTIVE_MACHINE_NAMES
    }
    default_machine = max(
        snapshots,
        key=lambda machine: abs(float(snapshots[machine].get("total_kw") or 0.0)),
        default=DEVICES[0]["name"],
    )
    components.html(
        build_streaming_dashboard_html(default_machine, get_lan_ip(), STREAM_PORT, view_mode="dashboard"),
        height=1320,
        scrolling=False,
    )

    st.divider()
    st.subheader("Live Machine State")
    _machine_state_panel()

    close_shell()


if __name__ == "__main__":
    main()
