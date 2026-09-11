import subprocess
import sys
import os
import socket
import ssl
from pathlib import Path
from urllib.request import urlopen

from utils.network import get_lan_ip

try:
    from config.settings import DEVICES
except Exception:
    DEVICES = []

SERVER_PORT = 8501
TCP_PROBE_TIMEOUT = 2.0

# Fix for UnicodeEncodeError on some Windows environments
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Older python versions
        pass

def start_application():
    """
    BACKEND ENTRY POINT.
    Run this file to launch the entire Web Application.
    This file itself will not be visible in the user interface.
    """
    print("🚀 Initializing Digital Transformation Ecosystem...")
    print("---")

    # NOTE: the pre-flight TCP probe was removed. These SELC AC-S2E gateways only
    # accept ONE TCP client at a time, so a probe connection here competes with the
    # background fetcher's own connection attempt a moment later and can starve it.
    # Use scripts/tcp_probe.py manually (with the app fully stopped) to diagnose
    # connectivity instead of probing on every launch.

    # Internal app UI logic
    ui_script = "app.py"
    cert_file = Path("certs") / "server.crt"
    key_file = Path("certs") / "server.key"
    
    if not os.path.exists(ui_script):
        print(f"❌ Error: {ui_script} not found!")
        return

    if not cert_file.exists() or not key_file.exists():
        cert_script = Path("scripts") / "create_streamlit_https_cert.ps1"
        if cert_script.exists():
            try:
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(cert_script),
                    ],
                    check=True,
                )
            except Exception as e:
                print(f"❌ Could not create HTTPS certificate: {e}")
                print("Run scripts\\create_streamlit_https_cert.ps1 manually, then start the app again.")
                return
        else:
            print("❌ HTTPS certificate files are missing.")
            print("Run scripts\\create_streamlit_https_cert.ps1, then start the app again.")
            return

    if _is_streamlit_https_running(SERVER_PORT):
        _print_existing_portal_message()
        return

    if _is_port_in_use("127.0.0.1", SERVER_PORT):
        print(f"❌ Port {SERVER_PORT} is already in use, but it is not responding as this HTTPS portal.")
        print("Stop the process using that port, or run: pm2 restart digital-transformation-portal")
        return

    # Trigger Streamlit Web server for the preview
    print(f"🖥️ Launching Dashboard and Backend Services...")
    try:
        # Using sys.executable to ensure we use the same Python environment
        # and 'python -m streamlit' for better compatibility
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                ui_script,
                "--server.address=0.0.0.0",
                f"--server.port={SERVER_PORT}",
                "--server.sslCertFile",
                str(cert_file),
                "--server.sslKeyFile",
                str(key_file),
            ]
        )
    except KeyboardInterrupt:
        print("\n🛑 Application stopped.")
    except Exception as e:
        print(f"❌ Runtime Error: {e}")


def _probe_tcp(host: str, port: int, timeout: float = TCP_PROBE_TIMEOUT) -> str:
    """Raw TCP reachability check (no Modbus). Tells TCP-level from Modbus-level faults."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(timeout)
        try:
            rc = probe.connect_ex((host, port))
        except Exception as exc:
            return f"ERROR ({exc})"
    if rc == 0:
        return "OPEN"
    if rc in (61, 111, 10061):
        return f"REFUSED (device up, port not listening) rc={rc}"
    if rc in (10060, 10035):
        return "TIMEOUT (SYN dropped - no TCP path to device) rc=%d" % rc
    return f"FAIL (rc={rc})"


def _run_connectivity_probe():
    """Print a quick TCP reachability report for every configured device port."""
    if not DEVICES:
        return
    print("🔌 Device connectivity check (TCP data ports):")
    for device in DEVICES:
        name = device.get("name", "?")
        host = device.get("host", "?")
        port = int(device.get("port", 0))
        status = _probe_tcp(host, port)
        icon = "✅" if status == "OPEN" else "❌"
        print(f"   {icon} {name:<22} {host}:{port:<6} -> {status}")
    print("---")


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((host, port)) == 0


def _is_streamlit_https_running(port: int) -> bool:
    context = ssl._create_unverified_context()
    try:
        response = urlopen(f"https://127.0.0.1:{port}/_stcore/health", context=context, timeout=3)
        return response.read().decode("utf-8").strip() == "ok"
    except Exception:
        return False


def _print_existing_portal_message():
    lan_ip = get_lan_ip()
    print(f"✅ Web portal is already running on HTTPS port {SERVER_PORT}.")
    print("")
    print("Open on this computer:")
    print(f"  https://localhost:{SERVER_PORT}/Live_Data")
    print("")
    print("Open from another computer on the same Wi-Fi:")
    print(f"  https://{lan_ip}:{SERVER_PORT}/Live_Data")
    print("")
    print("To restart the running portal:")
    print("  pm2 restart digital-transformation-portal")


if __name__ == "__main__":
    start_application()
