import datetime
import time
import logging
import threading
import socket
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.framer import FramerType
from pymodbus.payload import BinaryPayloadDecoder # type: ignore

# SELC AC-S2E converters run as transparent serial<->Ethernet bridges: the
# meter speaks Modbus RTU (with CRC) straight over the TCP socket, not the
# standard Modbus-TCP/MBAP framing. Probe RTU first since that's the gateway's
# actual mode, then fall back to plain Modbus-TCP for devices wired differently.
CANDIDATE_FRAMERS = [FramerType.RTU, FramerType.SOCKET]
device_framers = {}

from config.settings import (
    DEVICES, REGISTER_MAPPING, DB_COLUMNS, MACHINE_TABLE_MAPPING,
    SLAVE_ID, SLEEP_INTERVAL, CONNECT_TIMEOUT, MAX_RETRY_WAIT,
    HANDSHAKE_INTERVAL_SECONDS, PORT_PROBE_INTERVAL_SECONDS
)
from utils.db_handler import init_postgres_db, init_sqlite_db, save_to_sqlite, insert_to_postgres

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

stop_event = threading.Event()
device_profiles = {}
device_ports = {}
device_status = {}
active_clients = {}  # device_name -> live ModbusTcpClient, closed on shutdown

def sanitize_sqlite_table_name(name):
    return MACHINE_TABLE_MAPPING.get(name, name.lower().replace(" ", "_"))

def _set_immediate_reset_on_close(client):
    """Configure SO_LINGER=0 so closing the socket sends a TCP RST instead of a
    graceful FIN. SELC AC-S2E gateways allow only ONE TCP client at a time and
    hold a dropped connection's slot open for their idle-timeout (minutes). An RST
    tells the gateway immediately that the connection is dead, freeing the slot so
    the next run/connection isn't locked out. This also applies if the process is
    killed abruptly (Ctrl+C), since the OS closes the socket with the linger set."""
    try:
        sock = getattr(client, "socket", None)
        if sock is not None:
            import struct
            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_LINGER,
                struct.pack("ii", 1, 0),  # l_onoff=1, l_linger=0 -> RST on close
            )
    except Exception:
        pass


def connect_modbus(host, port, device_name, timeout, framer=FramerType.SOCKET):
    """Attempt one connection, return client on success or None on failure."""
    try:
        client = ModbusTcpClient(host=host, port=port, timeout=timeout, framer=framer)
        if client.connect():
            _set_immediate_reset_on_close(client)
            active_clients[device_name] = client
            logging.info(f"[{device_name}] Connected to {host}:{port} (framer={framer})")
            return client
        else:
            client.close()
            logging.warning(f"[{device_name}] Unable to connect to {host}:{port}")
            return None
    except Exception as exc:
        logging.warning(f"[{device_name}] Connection failed: {exc}")
        return None

def is_host_reachable(host, timeout=0.5):
    """Fast TCP/IP reachability hint used only for backend diagnostics."""
    try:
        socket.gethostbyaddr(host)
        return True
    except Exception:
        pass

    # ICMP requires platform-specific handling; a closed TCP connect still proves routing.
    for port in (23, 502):
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            probe.settimeout(timeout)
            result = probe.connect_ex((host, port))
            if result in (0, 10061):
                return True
        except Exception:
            pass
        finally:
            try:
                probe.close()
            except Exception:
                pass
    return False

def get_candidate_ports(device):
    ports = []
    for port in [device.get("port"), *device.get("candidate_ports", [])]:
        if port and port not in ports:
            ports.append(int(port))
    return ports

def get_endian(value):
    return Endian.BIG if value == "BIG" else Endian.LITTLE

def read_register(client, address, profile, retries):
    last_error = None
    for _ in range(retries):
        try:
            offset = profile.get("address_offset", 0)
            slave_id = profile["slave_id"]
            register_type = profile["register_type"]
            target_address = address + offset

            if register_type == "holding":
                result = client.read_holding_registers(target_address, 2, slave=slave_id)
            else:
                result = client.read_input_registers(target_address, 2, slave=slave_id)
            if result is None or result.isError():
                last_error = RuntimeError(f"Modbus {register_type} register read error")
                continue
            decoder = BinaryPayloadDecoder.fromRegisters(
                result.registers,
                byteorder=get_endian(profile["byteorder"]),
                wordorder=get_endian(profile["wordorder"]),
            )
            return round(decoder.decode_32bit_float(), 2)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(last_error or "Modbus read error")

def get_probe_profiles(device, default_slave_id):
    profiles = device.get("probe_profiles")
    if profiles:
        return profiles
    return [
        {
            "register_type": "input",
            "slave_id": default_slave_id,
            "byteorder": "BIG",
            "wordorder": "LITTLE",
            "address_offset": 0,
        }
    ]

def read_device_packet(client, register_mapping, profile, retries):
    data_packet = {}
    successful_reads = 0
    non_zero_reads = 0

    for label, address in register_mapping.items():
        try:
            value = read_register(client, address, profile, retries)
            data_packet[label] = value
            successful_reads += 1
            if value not in (0, 0.0):
                non_zero_reads += 1
        except Exception as exc:
            data_packet[label] = "Error"
            logging.warning(f"[{profile['register_type']} slave {profile['slave_id']}] {label} read failed: {exc}")

    return data_packet, successful_reads, non_zero_reads

def handshake_profile(client, profile, retries):
    """Read one small register group to prove the selected Modbus profile is alive."""
    first_label, first_address = next(iter(REGISTER_MAPPING.items()))
    try:
        value = read_register(client, first_address, profile, retries)
        return value not in (None, "Error")
    except Exception:
        return False

def probe_device_endpoint(device, probe_profiles, read_retries):
    """Find a working Modbus TCP port/profile without involving the frontend."""
    device_name = device["name"]
    host = device["host"]
    timeout = min(float(device.get("timeout", CONNECT_TIMEOUT)), 1.0)

    for port in get_candidate_ports(device):
        for framer in CANDIDATE_FRAMERS:
            client = connect_modbus(host, port, device_name, timeout, framer=framer)
            if client is None or not client.is_socket_open():
                continue

            try:
                for profile in probe_profiles:
                    if handshake_profile(client, profile, read_retries):
                        logging.info(
                            "[%s] Backend handshake OK on %s:%s with profile %s (framer=%s)",
                            device_name, host, port, profile, framer,
                        )
                        device_framers[device_name] = framer
                        return port, profile
            finally:
                try:
                    client.close()
                except Exception:
                    pass

    reachable_note = "reachable by LAN discovery/ping" if is_host_reachable(host) else "not reachable"
    logging.warning(
        "[%s] No Modbus data endpoint found on %s. Device is %s; check SELC AC-S2E TCP server/data port settings.",
        device_name,
        host,
        reachable_note,
    )
    return None, None

def is_packet_valid(data_packet):
    """A valid meter packet has at least one decoded non-zero telemetry value."""
    return any(
        data_packet.get(label) not in (None, "Error", 0, 0.0)
        for label in REGISTER_MAPPING.keys()
    )

def poll_device(device):
    device_name = device["name"]
    host = device["host"]
    port = device_ports.get(device_name, device["port"])
    client      = None
    timeout = device.get("timeout", CONNECT_TIMEOUT)
    slave_id = device.get("slave_id", SLAVE_ID)
    read_retries = max(1, int(device.get("read_retries", 1)))
    probe_profiles = get_probe_profiles(device, slave_id)
    
    postgres_table = MACHINE_TABLE_MAPPING.get(device_name)
    sqlite_table = sanitize_sqlite_table_name(device_name)
    next_endpoint_probe = 0
    next_handshake = 0
    next_connect_attempt = 0
    # After a failed connect, wait this long before retrying. The SELC gateways
    # only allow one TCP client and need a moment to release a dropped slot;
    # hammering every second keeps them permanently wedged.
    connect_backoff = float(device.get("connect_backoff", 6))

    consecutive_connect_failures = 0
    consecutive_zero_reads = 0
    OFFLINE_BACKOFF_AFTER = 3    # consecutive failures before 60s sleep
    ZERO_CACHE_RESET_AFTER = 10  # consecutive all-zero reads before profile re-scan

    while not stop_event.is_set():
        cycle_start = time.time()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_packet = {"Timestamp": timestamp}
        successful_reads = 0
        best_packet = None
        best_non_zero_reads = -1
        active_profiles = []
        valid_packet = False

        now = time.time()

        if client is not None and client.is_socket_open() and now >= next_handshake:
            cached_profile = device_profiles.get(device_name)
            if cached_profile and not handshake_profile(client, cached_profile, read_retries):
                logging.warning("[%s] Periodic backend handshake failed; reconnecting.", device_name)
                try:
                    client.close()
                except Exception:
                    pass
                client = None
            next_handshake = now + HANDSHAKE_INTERVAL_SECONDS

        if (client is None or not client.is_socket_open()) and now >= next_endpoint_probe and now >= next_connect_attempt:
            discovered_port, discovered_profile = probe_device_endpoint(device, probe_profiles, read_retries)
            if discovered_port is not None:
                port = discovered_port
                device_ports[device_name] = discovered_port
            if discovered_profile is not None:
                device_profiles[device_name] = discovered_profile
            next_endpoint_probe = now + PORT_PROBE_INTERVAL_SECONDS

        # Attempt to ensure connection is open, but not more often than the
        # backoff interval, so we don't re-wedge the single-slot gateway.
        if (client is None or not client.is_socket_open()) and now >= next_connect_attempt:
            framer = device_framers.get(device_name, FramerType.RTU)
            client = connect_modbus(host, port, device_name, timeout, framer=framer)
            if client is None:
                consecutive_connect_failures += 1
                if consecutive_connect_failures >= OFFLINE_BACKOFF_AFTER:
                    logging.warning(f"[{device_name}] offline — retrying in 60s")
                    next_connect_attempt = now + 60
                    consecutive_connect_failures = 0
                else:
                    next_connect_attempt = now + connect_backoff
            else:
                consecutive_connect_failures = 0

        if client is not None and client.is_socket_open():
            cached_profile = device_profiles.get(device_name)
            if cached_profile:
                active_profiles.append(cached_profile)
            active_profiles.extend(
                profile for profile in probe_profiles if profile != cached_profile
            )

            selected_profile = None
            for profile in active_profiles:
                profile_packet, profile_successful_reads, non_zero_reads = read_device_packet(
                    client, REGISTER_MAPPING, profile, read_retries
                )

                if profile_successful_reads > successful_reads:
                    successful_reads = profile_successful_reads
                    data_packet.update(profile_packet)

                if non_zero_reads > best_non_zero_reads:
                    best_non_zero_reads = non_zero_reads
                    best_packet = profile_packet

                if non_zero_reads > 0:
                    selected_profile = profile
                    data_packet.update(profile_packet)
                    successful_reads = profile_successful_reads
                    break

            if selected_profile is not None:
                if device_profiles.get(device_name) != selected_profile:
                    logging.info(f"[{device_name}] Using profile: {selected_profile}")
                device_profiles[device_name] = selected_profile
                device_ports[device_name] = port
                device_status[device_name] = {
                    "online": True,
                    "host": host,
                    "port": port,
                    "last_handshake": datetime.datetime.now().isoformat(timespec="seconds"),
                }
                valid_packet = True
                consecutive_zero_reads = 0
            elif best_packet is not None:
                data_packet.update(best_packet)
                valid_packet = is_packet_valid(data_packet)

            if successful_reads == 0:
                # Reads failed on every profile. If the TCP socket is STILL open,
                # this is a Modbus/serial-layer issue (wrong slave id / register /
                # or the converter<->meter RS-485 serial settings don't match the
                # meter) - NOT a broken TCP link. Closing + reconnecting here just
                # re-wedges the single-slot SELC gateway and locks us out, so keep
                # the socket open and keep retrying reads on it.
                if client is not None and client.is_socket_open():
                    logging.warning(
                        f"[{device_name}] Connected but no register decoded "
                        f"(check meter slave id / Serial Port Settings baud/parity); keeping connection open."
                    )
                else:
                    logging.warning(f"[{device_name}] Connection dropped during read; will reconnect.")
                    try:
                        if client is not None:
                            client.close()
                    except Exception:
                        pass
                    client = None
            elif best_non_zero_reads == 0:
                # Reads succeeded but every value was zero - this is a LEGITIMATE
                # state (machine idle/powered off), not a broken connection. These
                # SELC AC-S2E gateways only accept ONE TCP client at a time, so
                # closing/reconnecting here thrashes the single connection slot and
                # can lock the app out entirely. Keep the socket open.
                consecutive_zero_reads += 1
                if consecutive_zero_reads >= ZERO_CACHE_RESET_AFTER:
                    logging.warning(
                        f"[{device_name}] {ZERO_CACHE_RESET_AFTER} consecutive all-zero reads; "
                        f"invalidating profile cache and re-scanning."
                    )
                    device_profiles.pop(device_name, None)
                    next_endpoint_probe = 0
                    consecutive_zero_reads = 0
                else:
                    logging.info(f"[{device_name}] All-zero telemetry (machine likely idle); keeping connection open.")
        else:
            logging.warning(f"[{device_name}] Device offline - no Modbus handshake; writing diagnostic zero packet.")
            device_status[device_name] = {
                "online": False,
                "host": host,
                "port": port,
                "last_handshake": None,
            }
            for label in REGISTER_MAPPING:
                if label not in data_packet or data_packet[label] == "Error":
                    data_packet[label] = 0.0

        if postgres_table:
            try:
                insert_to_postgres(postgres_table, data_packet, timestamp)
            except Exception as e:
                logging.error(f"[{device_name}] DB insert error: {e}")

        def _is_zero(v):
            return v is None or v == "Error" or v == 0 or v == 0.0

        avg_vln = data_packet.get("Avg Voltage LN")
        avg_vll = data_packet.get("Avg Voltage LL")
        avg_cur = data_packet.get("Avg Current")
        total_kw_val = data_packet.get("Total KW")
        total_kwh_val = data_packet.get("Total net kWh")

        all_zero = (
            _is_zero(avg_vln) and _is_zero(avg_vll) and _is_zero(avg_cur)
            and _is_zero(total_kw_val) and _is_zero(total_kwh_val)
        )

        if not all_zero:
            kw = float(total_kw_val) if not _is_zero(total_kw_val) else 0.0
            if kw < 2.82:
                state = {"state_label": "IDLE", "p_idle": 1.0, "p_working": 0.0}
            elif kw > 3.05:
                state = {"state_label": "WORKING", "p_idle": 0.0, "p_working": 1.0}
            else:
                state = {"state_label": "TRANSITION", "p_idle": 0.5, "p_working": 0.5}
            try:
                save_to_sqlite(sqlite_table, data_packet, DB_COLUMNS, state=state)
            except Exception as exc:
                logging.error(f"[{device_name}] SQLite save error: {exc}")

        # Precise 1-second interval tracking
        elapsed = time.time() - cycle_start
        sleep_time = max(0, SLEEP_INTERVAL - elapsed)
        stop_event.wait(sleep_time)

def run_fetcher():
    logging.info("Starting background data fetcher...")
    # Ensure gateway sockets are closed (RST) on any interpreter exit, so the
    # single-connection SELC converters don't stay locked for the next launch.
    import atexit
    atexit.register(close_all_clients)
    init_postgres_db()
    init_sqlite_db(DEVICES, sanitize_sqlite_table_name)

    threads = []
    for device in DEVICES:
        t = threading.Thread(target=poll_device, args=(device,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.1) # Faster staggered start

    logging.info(f"Background fetcher running - polling {len(DEVICES)} device(s) every 1s.")
    return threads

def close_all_clients():
    """Close every live gateway connection with an RST so the single-slot SELC
    gateways release their connection slot immediately, instead of leaving a ghost
    that blocks the next run for minutes."""
    for name, client in list(active_clients.items()):
        try:
            client.close()
        except Exception:
            pass
        active_clients.pop(name, None)


def stop_fetcher():
    stop_event.set()
    close_all_clients()
    logging.info("Background fetcher stop signal sent; connections closed.")
