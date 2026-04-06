import socket
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

from services.telemetry_stream import STREAM_HOST, STREAM_PORT


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


@lru_cache(maxsize=1)
def ensure_telemetry_server_process():
    if _is_port_open(STREAM_HOST, STREAM_PORT):
        return True

    subprocess.Popen(
        [sys.executable, "-m", "services.telemetry_stream"],
        cwd=str(Path(__file__).resolve().parents[1]),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    for _ in range(20):
        if _is_port_open(STREAM_HOST, STREAM_PORT):
            return True
        time.sleep(0.3)
    return False
