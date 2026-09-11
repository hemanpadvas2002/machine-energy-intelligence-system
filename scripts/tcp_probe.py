"""Standalone TCP reachability probe for the CNC Modbus gateways.

Run this to prove whether the PROBLEM is TCP-level (can't even open a socket)
or Modbus-level (socket opens but no valid Modbus data). It does NOT use
pymodbus at all -- it only tests whether a raw TCP connection can be opened.

Usage:
    python scripts/tcp_probe.py
"""
import socket
import sys

# (label, host, primary_port, [all ports to test])
TARGETS = [
    ("Galaxy_CNC",          "192.168.1.182", [522, 502, 23, 4001, 5000, 10001]),
    ("Ace_Vantage_CNC",     "192.168.1.183", [523, 502, 23, 4001, 5000, 10001]),
    ("LML_GRINDMASTER_CNC", "192.168.1.184", [524, 502, 23, 4001, 5000, 10001]),
    ("AGI_ROBO_CNC",        "192.168.1.186", [526, 502, 23, 4001, 5000, 10001]),
]

TIMEOUT = 2.0


def probe(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    try:
        rc = s.connect_ex((host, port))
        if rc == 0:
            return "OPEN"
        # errno 111/10061 = actively refused (host up, nothing listening)
        if rc in (61, 111, 10061):
            return f"REFUSED (rc={rc})"
        return f"FAIL (rc={rc})"
    except socket.timeout:
        return "TIMEOUT"
    except Exception as exc:
        return f"ERROR ({exc})"
    finally:
        s.close()


def main():
    print(f"Local host: {socket.gethostbyname(socket.gethostname())}")
    print(f"TCP connect timeout: {TIMEOUT}s\n")
    for label, host, ports in TARGETS:
        print(f"=== {label} @ {host} ===")
        for port in ports:
            print(f"  {host}:{port:<6} -> {probe(host, port)}")
        print()


if __name__ == "__main__":
    sys.exit(main())
