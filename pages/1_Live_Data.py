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


apply_page_config("AMTDC Live Data")

_DB_COLS = {
    "timestamp":      "Timestamp",
    "avg_voltage_ln": "Voltage (V)",
    "avg_current":    "Current (A)",
    "total_kw":       "Power (kW)",
    "total_net_kwh":  "Energy (kWh)",
    "state_label":    "State",
}


def _fetch_last_rows(table: str, n: int = 30) -> pd.DataFrame:
    try:
        cols = ", ".join(_DB_COLS.keys())
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            df = pd.read_sql_query(
                f"SELECT {cols} FROM {table} ORDER BY id DESC LIMIT {n}",
                conn,
            )
        return df.rename(columns=_DB_COLS)
    except Exception:
        return pd.DataFrame()


@st.fragment(run_every=2)
def _data_panel(machine: str) -> None:
    table = MACHINE_TABLE_MAPPING.get(machine)
    df = _fetch_last_rows(table) if table else pd.DataFrame()

    if df.empty:
        st.info(f"No data yet for **{machine}** — waiting for the first reading…")
        return

    latest = df.iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Voltage",  f"{float(latest.get('Voltage (V)',  0.0) or 0.0):.1f} V")
    c2.metric("Current",  f"{float(latest.get('Current (A)',  0.0) or 0.0):.2f} A")
    c3.metric("Power",    f"{float(latest.get('Power (kW)',   0.0) or 0.0):.3f} kW")
    c4.metric("State",    str(latest.get("State") or "—"))

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Timestamp":    st.column_config.TextColumn("Timestamp",    width="medium"),
            "Voltage (V)":  st.column_config.NumberColumn("Voltage (V)",  format="%.1f",  width="small"),
            "Current (A)":  st.column_config.NumberColumn("Current (A)",  format="%.2f",  width="small"),
            "Power (kW)":   st.column_config.NumberColumn("Power (kW)",   format="%.3f",  width="small"),
            "Energy (kWh)": st.column_config.NumberColumn("Energy (kWh)", format="%.2f",  width="small"),
            "State":        st.column_config.TextColumn("State",          width="small"),
        },
    )


def main():
    ensure_telemetry_server_process()

    inject_styles()
    render_sidebar("Live Data")
    render_shell("Live Data", "Telemetry", "Digital Transformation Dashboard", "Live Data")

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
        build_streaming_dashboard_html(default_machine, get_lan_ip(), STREAM_PORT, view_mode="live"),
        height=1320,
        scrolling=False,
    )

    st.divider()
    st.subheader("Live Readings")

    machine_names = list(MACHINE_TABLE_MAPPING.keys())
    selected = st.selectbox(
        "Machine",
        options=machine_names,
        index=machine_names.index(default_machine) if default_machine in machine_names else 0,
        key="data_panel_machine",
        label_visibility="collapsed",
    )

    _data_panel(selected)

    close_shell()


if __name__ == "__main__":
    main()
