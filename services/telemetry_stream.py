import json
import logging
import threading
from collections import Counter
from datetime import datetime
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from config.settings import MACHINE_TABLE_MAPPING
from services.matlab_analytics import get_matlab_analytics_service
from utils.db_handler import (
    fetch_incremental_points_from_postgres,
    fetch_latest_machine_snapshots,
    fetch_recent_points_from_postgres,
)


logger = logging.getLogger(__name__)

STREAM_HOST = "127.0.0.1"
STREAM_PORT = 8765
WINDOW_SIZE = 60
MODE_LIMIT = 5

PARAMETER_FIELDS = {
    "avg_voltage_ln": "avg_voltage_ln",
    "avg_voltage_ll": "avg_voltage_ll",
    "avg_current": "avg_current",
    "total_kw": "total_kw",
    "total_net_kwh": "total_net_kwh",
}

MODE_TONES = ["#0b7171", "#1f8d8d", "#4b6e90", "#a47400", "#cf2e2e"]


def _serialize_point(row, parameter):
    value = row.get(parameter)
    return {
        "timestamp": row["timestamp"].isoformat(),
        "value": float(value) if value is not None else 0.0,
    }


def _compute_modes(points):
    values = [round(float(point["value"]), 2) for point in points if float(point["value"]) != 0.0]
    counts = Counter(values).most_common(MODE_LIMIT)
    modes = []
    for index, (value, hits) in enumerate(counts, start=1):
        modes.append(
            {
                "label": f"MOD-{index:02d}",
                "value": float(value),
                "hits": int(hits),
                "tone": MODE_TONES[index - 1],
            }
        )
    return modes


def build_dashboard_payload(machine, parameter="total_kw", since=None):
    table = MACHINE_TABLE_MAPPING.get(machine)
    if not table:
        return {"error": f"Unknown machine: {machine}"}, 404

    parameter = PARAMETER_FIELDS.get(parameter, "total_kw")
    latest_rows = fetch_latest_machine_snapshots()
    kpi_rows = list(latest_rows.values())
    kw_values = [float(row.get("total_kw") or 0.0) for row in kpi_rows]
    total_energy = sum(float(row.get("total_net_kwh") or 0.0) for row in kpi_rows)

    if since:
        series_df = fetch_incremental_points_from_postgres(table, since)
    else:
        series_df = fetch_recent_points_from_postgres(table, limit=WINDOW_SIZE)

    series = []
    if not series_df.empty:
        series = [
            _serialize_point(row, parameter)
            for row in series_df[["timestamp", parameter]].to_dict(orient="records")
        ]

    window_df = fetch_recent_points_from_postgres(table, limit=WINDOW_SIZE)
    window_series = []
    if not window_df.empty:
        window_series = [
            _serialize_point(row, parameter)
            for row in window_df[["timestamp", parameter]].to_dict(orient="records")
        ]

    latest_machine_rows = []
    for machine_name, row in latest_rows.items():
        load_kw = float(row.get("total_kw") or 0.0)
        latest_machine_rows.append(
            {
                "machine": machine_name,
                "load_kw": load_kw,
                "state": "Optimal" if load_kw > 0 else "Idle",
                "last_sync": row["timestamp"].isoformat(),
            }
        )

    payload = {
        "machine": machine,
        "parameter": parameter,
        "generated_at": datetime.utcnow().isoformat(),
        "replace": since is None,
        "points": series,
        "window": window_series,
        "kpis": {
            "total_energy": round(total_energy, 2),
            "active_machines": len(latest_rows),
            "machine_count": len(MACHINE_TABLE_MAPPING),
            "average_load": round(sum(kw_values) / len(kw_values), 2) if kw_values else 0.0,
            "peak_demand": round(max(kw_values), 2) if kw_values else 0.0,
        },
        "machines": latest_machine_rows,
        "modes": _compute_modes(window_series),
        "zero_only_signal": bool(window_series) and all(point["value"] == 0.0 for point in window_series),
    }
    return payload, 200


def _build_series(machine, parameter="total_kw", window_size=WINDOW_SIZE):
    table = MACHINE_TABLE_MAPPING.get(machine)
    if not table:
        return None, {"error": f"Unknown machine: {machine}"}, 404

    parameter = PARAMETER_FIELDS.get(parameter, "total_kw")
    window_df = fetch_recent_points_from_postgres(table, limit=window_size)
    if window_df.empty:
        payload = {
            "machine": machine,
            "parameter": parameter,
            "timestamps": [],
            "values": [],
            "filtered": [],
            "smoothed": [],
            "fft_frequency": [],
            "fft": [],
            "engine": "empty",
            "zero_only_signal": False,
            "generated_at": datetime.utcnow().isoformat(),
        }
        return [], payload, 200

    timestamps = [row.isoformat() for row in window_df["timestamp"].tolist()]
    values = [float(value or 0.0) for value in window_df[parameter].tolist()]
    latest_timestamp = timestamps[-1] if timestamps else "empty"
    cache_key = (machine, parameter, latest_timestamp, len(values))
    result = get_matlab_analytics_service().process_series(
        timestamps,
        values,
        sample_interval=1.0,
        cache_key=cache_key,
    )
    payload = {
        "machine": machine,
        "parameter": parameter,
        "generated_at": datetime.utcnow().isoformat(),
        "zero_only_signal": bool(values) and all(value == 0.0 for value in values),
        **result.to_dict(),
    }
    return values, payload, 200


def build_filter_payload(machine, parameter="total_kw", window_size=WINDOW_SIZE):
    _, payload, status = _build_series(machine, parameter, window_size)
    if status != 200:
        return payload, status
    return {
        "machine": payload["machine"],
        "parameter": payload["parameter"],
        "timestamps": payload["timestamps"],
        "values": payload["values"],
        "filtered": payload["filtered"],
        "smoothed": payload["smoothed"],
        "engine": payload["engine"],
        "generated_at": payload["generated_at"],
        "zero_only_signal": payload["zero_only_signal"],
    }, 200


def build_fft_payload(machine, parameter="total_kw", window_size=WINDOW_SIZE):
    _, payload, status = _build_series(machine, parameter, window_size)
    if status != 200:
        return payload, status
    return {
        "machine": payload["machine"],
        "parameter": payload["parameter"],
        "timestamps": payload["timestamps"],
        "fft_frequency": payload["fft_frequency"],
        "fft": payload["fft"],
        "engine": payload["engine"],
        "generated_at": payload["generated_at"],
    }, 200


def build_timeseries_payload(machine, parameter="total_kw", window_size=WINDOW_SIZE):
    values, payload, status = _build_series(machine, parameter, window_size)
    if status != 200:
        return payload, status
    payload["modes"] = _compute_modes(
        [{"timestamp": timestamp, "value": value} for timestamp, value in zip(payload["timestamps"], values)]
    )
    return payload, 200


class TelemetryRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        machine = params.get("machine", [next(iter(MACHINE_TABLE_MAPPING.keys()))])[0]
        parameter = params.get("parameter", ["total_kw"])[0]
        since = params.get("since", [None])[0]
        window_size = int(params.get("window", [WINDOW_SIZE])[0])

        if parsed.path == "/api/telemetry/dashboard":
            payload, status = build_dashboard_payload(machine, parameter, since)
        elif parsed.path == "/api/matlab/fft":
            payload, status = build_fft_payload(machine, parameter, window_size)
        elif parsed.path == "/api/matlab/filter":
            payload, status = build_filter_payload(machine, parameter, window_size)
        elif parsed.path == "/api/matlab/timeseries":
            payload, status = build_timeseries_payload(machine, parameter, window_size)
        else:
            self._send_json({"error": "Not found"}, 404)
            return

        self._send_json(payload, status)

    def log_message(self, format, *args):
        logger.debug("Telemetry stream: " + format, *args)


@lru_cache(maxsize=1)
def start_telemetry_stream_server():
    try:
        server = ThreadingHTTPServer((STREAM_HOST, STREAM_PORT), TelemetryRequestHandler)
    except OSError:
        logger.info("Telemetry stream server already active on %s:%s", STREAM_HOST, STREAM_PORT)
        return None

    thread = threading.Thread(target=server.serve_forever, daemon=True, name="telemetry-stream-server")
    thread.start()
    return server


def run_telemetry_stream_server_forever():
    server = ThreadingHTTPServer((STREAM_HOST, STREAM_PORT), TelemetryRequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    run_telemetry_stream_server_forever()
