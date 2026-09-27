import json
import logging
import os
import threading
import time
from collections import Counter
from datetime import datetime, timedelta
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from config.settings import ACTIVE_MACHINE_NAMES, MACHINE_TABLE_MAPPING
from services.matlab_analytics import get_matlab_analytics_service
from utils.db_handler import (
    fetch_24h_peak_kw,
    fetch_incremental_points_from_postgres,
    fetch_latest_machine_snapshots,
    fetch_latest_valid_snapshots,
    fetch_recent_points_from_postgres,
)


logger = logging.getLogger(__name__)

STREAM_HOST = os.getenv("AMTDC_STREAM_HOST", "0.0.0.0")
STREAM_PORT = 8765
WINDOW_SIZE = 60
MODE_LIMIT = 5
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_REQUESTS = 240
_rate_limit_lock = threading.Lock()
_rate_limit_hits = {}

PARAMETER_FIELDS = {
    "avg_voltage_ln": "avg_voltage_ln",
    "avg_voltage_ll": "avg_voltage_ll",
    "avg_current": "avg_current",
    "total_kw": "total_kw",
    "total_net_kwh": "total_net_kwh",
}

MODE_TONES = ["#0b7171", "#1f8d8d", "#4b6e90", "#a47400", "#cf2e2e"]
TELEMETRY_COLUMNS = ["avg_voltage_ln", "avg_voltage_ll", "avg_current", "total_kw", "total_net_kwh"]


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


def _filter_valid_meter_rows(df):
    """Drop rows that are synthetic/offline all-zero packets."""
    if df.empty:
        return df
    available_columns = [column for column in TELEMETRY_COLUMNS if column in df.columns]
    if not available_columns:
        return df
    numeric = df[available_columns].fillna(0).astype(float).abs()
    return df[numeric.sum(axis=1) > 0].copy()


def build_dashboard_payload(machine, parameter="total_kw", since=None):
    table = MACHINE_TABLE_MAPPING.get(machine)
    if not table:
        return {"error": f"Unknown machine: {machine}"}, 404

    parameter = PARAMETER_FIELDS.get(parameter, "total_kw")

    # latest_rows: absolute most-recent row per machine (may be a zero/diagnostic
    # packet).  Used ONLY for the 60-second "is the machine still writing?" check.
    latest_rows = {
        m: row
        for m, row in fetch_latest_machine_snapshots().items()
        if m in ACTIVE_MACHINE_NAMES
    }

    # valid_rows: most-recent NON-ZERO row per machine.  Used for display values
    # (voltage, kW) so the fleet panel matches what the timeseries graph shows.
    valid_rows = {
        m: row
        for m, row in fetch_latest_valid_snapshots().items()
        if m in ACTIVE_MACHINE_NAMES
    }

    # Active = machine wrote ANY row (including zero heartbeat) in the last 60 s
    cutoff = datetime.utcnow() - timedelta(seconds=60)
    active_rows = {
        m: row for m, row in latest_rows.items()
        if row.get("timestamp") is not None
        and row["timestamp"].to_pydatetime().replace(tzinfo=None) > cutoff
    }

    total_energy = sum(float(row.get("total_net_kwh") or 0.0) for row in latest_rows.values())
    active_kw = [float(row.get("total_kw") or 0.0) for row in active_rows.values()]
    avg_kw = round(sum(active_kw) / len(active_kw), 3) if active_kw else 0.0

    # 24-hour peak across every configured machine table
    peak_kw_24h = max(
        (fetch_24h_peak_kw(t) for t in MACHINE_TABLE_MAPPING.values()),
        default=0.0,
    )

    if since:
        series_df = fetch_incremental_points_from_postgres(table, since)
    else:
        series_df = fetch_recent_points_from_postgres(table, limit=WINDOW_SIZE * 10)

    series_df = _filter_valid_meter_rows(series_df).tail(WINDOW_SIZE)

    series = []
    if not series_df.empty:
        series = [
            _serialize_point(row, parameter)
            for row in series_df[["timestamp", parameter]].to_dict(orient="records")
        ]

    window_df = _filter_valid_meter_rows(
        fetch_recent_points_from_postgres(table, limit=WINDOW_SIZE * 10)
    ).tail(WINDOW_SIZE)
    window_series = []
    if not window_df.empty:
        window_series = [
            _serialize_point(row, parameter)
            for row in window_df[["timestamp", parameter]].to_dict(orient="records")
        ]

    machine_list = []
    for m_name in latest_rows:
        # For the online/timestamp check: use latest_rows (includes zero heartbeats)
        ts = latest_rows[m_name].get("timestamp")
        is_online = m_name in active_rows
        # For display values: prefer valid_rows (last non-zero reading) so the
        # fleet panel voltage matches what the timeseries graph renders.
        display_row = valid_rows.get(m_name, latest_rows[m_name])
        load_kw = float(display_row.get("total_kw") or 0.0)
        machine_list.append({
            "machine": m_name,
            "load_kw": round(load_kw, 3),
            "avg_voltage_ln": round(float(display_row.get("avg_voltage_ln") or 0.0), 1),
            "online": is_online,
            "state": "WORKING" if abs(load_kw) > 0.01 else "IDLE",
            "last_sync": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
        })

    payload = {
        "machine": machine,
        "parameter": parameter,
        "generated_at": datetime.utcnow().isoformat(),
        "replace": since is None,
        "points": series,
        "window": window_series,
        "kpis": {
            "total_energy": round(total_energy, 2),
            "active_machines": len(active_rows),
            "machine_count": len(ACTIVE_MACHINE_NAMES),
            "average_load": avg_kw,
            "peak_demand": round(peak_kw_24h, 3),
        },
        "machines": machine_list,
        "modes": _compute_modes(window_series),
        "zero_only_signal": bool(window_series) and all(point["value"] == 0.0 for point in window_series),
    }
    return payload, 200


def _build_series(machine, parameter="total_kw", window_size=WINDOW_SIZE):
    table = MACHINE_TABLE_MAPPING.get(machine)
    if not table:
        return None, {"error": f"Unknown machine: {machine}"}, 404

    parameter = PARAMETER_FIELDS.get(parameter, "total_kw")
    window_df = _filter_valid_meter_rows(
        fetch_recent_points_from_postgres(table, limit=window_size * 10)
    ).tail(window_size)
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
            "no_valid_telemetry": True,
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
        "no_valid_telemetry": False,
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


def build_raw_payload(machine, limit=30):
    table = MACHINE_TABLE_MAPPING.get(machine)
    if not table:
        return {"error": f"Unknown machine: {machine}"}, 404

    df = _filter_valid_meter_rows(
        fetch_recent_points_from_postgres(table, limit=limit * 5)
    ).tail(limit)

    rows = []
    if not df.empty:
        for row in df.iloc[::-1].to_dict(orient="records"):
            ts = row.get("timestamp")
            rows.append({
                "timestamp":      ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "avg_voltage_ln": round(float(row.get("avg_voltage_ln") or 0.0), 2),
                "avg_current":    round(float(row.get("avg_current")    or 0.0), 3),
                "total_kw":       round(float(row.get("total_kw")       or 0.0), 3),
                "total_net_kwh":  round(float(row.get("total_net_kwh")  or 0.0), 2),
                "state_label":    str(row.get("state_label") or "—"),
            })

    return {"machine": machine, "rows": rows}, 200


class TelemetryRequestHandler(BaseHTTPRequestHandler):
    def _is_rate_limited(self):
        client_ip = self.client_address[0]
        now = time.monotonic()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        with _rate_limit_lock:
            hits = [hit for hit in _rate_limit_hits.get(client_ip, []) if hit >= window_start]
            hits.append(now)
            _rate_limit_hits[client_ip] = hits
            return len(hits) > RATE_LIMIT_REQUESTS

    def _send_security_headers(self, body_length):
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(body_length))
        self.send_header("Strict-Transport-Security", "max-age=31536000")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")

        origin = self.headers.get("Origin", "")
        if origin and origin != "null":
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        else:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._send_security_headers(len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self._is_rate_limited():
            self._send_json({"error": "Too many requests"}, 429)
            return

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        machine = params.get("machine", [next(iter(MACHINE_TABLE_MAPPING.keys()))])[0]
        parameter = params.get("parameter", ["total_kw"])[0]
        since = params.get("since", [None])[0]
        window_size = int(params.get("window", [WINDOW_SIZE])[0])

        if parsed.path == "/api/telemetry/dashboard":
            payload, status = build_dashboard_payload(machine, parameter, since)
        elif parsed.path == "/api/telemetry/raw":
            limit = int(params.get("limit", [30])[0])
            payload, status = build_raw_payload(machine, limit)
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

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_security_headers(0)
        self.end_headers()

    def log_message(self, format, *args):
        logger.debug("Telemetry stream: " + format, *args)


def _create_http_server():
    return ThreadingHTTPServer((STREAM_HOST, STREAM_PORT), TelemetryRequestHandler)


@lru_cache(maxsize=1)
def start_telemetry_stream_server():
    try:
        server = _create_http_server()
    except OSError:
        logger.info("Telemetry stream server already active on %s:%s", STREAM_HOST, STREAM_PORT)
        return None

    thread = threading.Thread(target=server.serve_forever, daemon=True, name="telemetry-stream-server")
    thread.start()
    return server


def run_telemetry_stream_server_forever():
    server = _create_http_server()
    server.serve_forever()


if __name__ == "__main__":
    run_telemetry_stream_server_forever()
