import streamlit as st
import streamlit.components.v1 as components

from config.settings import MACHINE_TABLE_MAPPING
from data_fetcher.modbus_fetcher import run_fetcher
from services.telemetry_runtime import ensure_telemetry_server_process
from services.telemetry_stream import STREAM_HOST, STREAM_PORT
from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar
from ui.streaming_dashboard import build_streaming_dashboard_html
from utils.db_handler import fetch_latest_machine_snapshots


apply_page_config("AMTDC Live Data")


@st.cache_resource
def start_background_services():
    try:
        run_fetcher()
    except Exception as exc:
        print(f"Error starting background services: {exc}")
    return True


def main():
    start_background_services()
    ensure_telemetry_server_process()

    inject_styles()
    render_sidebar("Live Data")
    render_shell("Live Data", "Telemetry", "Digital Transformation Dashboard", "Live Data")

    snapshots = fetch_latest_machine_snapshots()
    default_machine = max(
        snapshots,
        key=lambda machine: abs(float(snapshots[machine].get("total_kw") or 0.0)),
        default=next(iter(MACHINE_TABLE_MAPPING.keys())),
    )
    api_base_url = f"http://{STREAM_HOST}:{STREAM_PORT}"
    components.html(
        build_streaming_dashboard_html(default_machine, api_base_url, view_mode="live"),
        height=1320,
        scrolling=False,
    )

    close_shell()


if __name__ == "__main__":
    main()
