import streamlit as st
import streamlit.components.v1 as components

from config.settings import ACTIVE_MACHINE_NAMES, DEVICES, MACHINE_TABLE_MAPPING
from services.telemetry_runtime import ensure_telemetry_server_process
from services.telemetry_stream import STREAM_PORT
from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar
from ui.streaming_dashboard import build_streaming_dashboard_html
from utils.db_handler import fetch_latest_machine_snapshots
from utils.network import get_lan_ip


apply_page_config("AMTDC Dashboard")


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

    close_shell()


if __name__ == "__main__":
    main()
