"""
START.py — Single entry point for Machine Energy Intelligence System
Place this file in the project root directory.

Usage:
  python START.py

What it does:
  1. Checks Python dependencies are installed
  2. Initialises SQLite database tables
  3. Starts Modbus data fetcher (background daemon threads)
  4. Launches Streamlit dashboard in a subprocess
  5. Keeps running — Ctrl+C to stop everything cleanly
"""

import sys
import os
import subprocess
import threading
import time
import signal
import importlib

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

def check_deps():
    """Verify required packages are installed."""
    checks = {
        "streamlit": "streamlit",
        "pandas": "pandas",
        "plotly": "plotly",
        "scipy": "scipy",
        "pymodbus": "pymodbus",
        "psycopg2": "psycopg2",
    }
    missing = []
    for pkg, mod in checks.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[START] Missing packages: {', '.join(missing)}")
        print(f"[START] Run:  pip install {' '.join(missing)}")
        sys.exit(1)
    print("[START] All dependencies present")

def init_db():
    """Initialise SQLite database with per-machine tables."""
    import sqlite3
    from config.settings import SQLITE_DB, MACHINE_TABLE_MAPPING

    db_dir = os.path.dirname(SQLITE_DB) or "."
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()

    for device_name, table_name in MACHINE_TABLE_MAPPING.items():
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL,
                avg_voltage_ln REAL,
                avg_voltage_ll REAL,
                avg_current REAL,
                total_kw    REAL,
                total_net_kwh REAL
            )
        """)

    conn.commit()
    conn.close()
    print(f"[START] SQLite DB initialised — {SQLITE_DB}")

def start_fetcher():
    """Start Modbus data fetcher in background thread."""
    from data_fetcher.modbus_fetcher import run_fetcher
    t = threading.Thread(target=run_fetcher, daemon=True, name="ModbusFetcher")
    t.start()
    print("[START] Modbus fetcher started")
    return t

STREAMLIT_PORT = 8501

def start_streamlit():
    """Launch Streamlit dashboard subprocess."""
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", str(STREAMLIT_PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]

    # Check for HTTPS certs and add if present
    cert_dir = os.path.join(ROOT, "certs")
    cert = os.path.join(cert_dir, "server.crt")
    key = os.path.join(cert_dir, "server.key")

    if os.path.isfile(cert) and os.path.isfile(key):
        cmd += ["--server.sslCertFile", cert, "--server.sslKeyFile", key]
        proto = "https"
    else:
        proto = "http"

    proc = subprocess.Popen(cmd, cwd=ROOT)
    print(f"[START] Streamlit at {proto}://localhost:{STREAMLIT_PORT}")
    return proc

def main():
    """Main entry point."""
    print("=" * 70)
    print("  Machine Energy Intelligence System")
    print("=" * 70)

    check_deps()
    init_db()
    start_fetcher()
    streamlit_proc = start_streamlit()
    time.sleep(3)

    print("\n[START] System is LIVE. Press Ctrl+C to stop.\n")

    def shutdown(sig=None, frame=None):
        """Clean shutdown on SIGINT/SIGTERM."""
        print("\n[START] Shutting down...")
        streamlit_proc.terminate()
        try:
            streamlit_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            streamlit_proc.kill()
        print("[START] Done.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Monitor Streamlit and restart if it crashes
    while True:
        if streamlit_proc.poll() is not None:
            print("[START] Streamlit exited — restarting...")
            streamlit_proc = start_streamlit()
        time.sleep(5)

if __name__ == "__main__":
    main()
