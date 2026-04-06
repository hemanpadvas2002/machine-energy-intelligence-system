import datetime
import time
import logging
import threading
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder # type: ignore

from config.settings import (
    DEVICES, REGISTER_MAPPING, DB_COLUMNS, MACHINE_TABLE_MAPPING,
    SLAVE_ID, SLEEP_INTERVAL, CONNECT_TIMEOUT, MAX_RETRY_WAIT
)
from utils.db_handler import init_postgres_db, init_sqlite_db, save_to_sqlite, insert_to_postgres

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

stop_event = threading.Event()
device_profiles = {}

def sanitize_sqlite_table_name(name):
    mapping = {
        "Galaxy_CNC":          "galaxy_readings",
        "MTX_CNC":             "mtx_readings",
        "LML_GRINDMASTER_CNC": "lml_upmmc_readings",
        "AGI_ROBO_CNC":        "agi_robo_readings",
        "Ace_Vantage_CNC":     "ace_vantage_readings",
    }
    return mapping.get(name, name.lower().replace(" ", "_") + "_readings")

def connect_modbus(host, port, device_name, timeout):
    """Attempt one connection, return client on success or None on failure."""
    try:
        client = ModbusTcpClient(host=host, port=port, timeout=timeout)
        if client.connect():
            logging.info(f"[{device_name}] Connected to {host}:{port}")
            return client
        else:
            client.close()
            logging.warning(f"[{device_name}] Unable to connect to {host}:{port}")
            return None
    except Exception as exc:
        logging.warning(f"[{device_name}] Connection failed: {exc}")
        return None

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

def poll_device(device):
    device_name = device["name"]
    host, port  = device["host"], device["port"]
    client      = None
    timeout = device.get("timeout", CONNECT_TIMEOUT)
    slave_id = device.get("slave_id", SLAVE_ID)
    read_retries = max(1, int(device.get("read_retries", 1)))
    probe_profiles = get_probe_profiles(device, slave_id)
    
    postgres_table = MACHINE_TABLE_MAPPING.get(device_name)
    sqlite_table = sanitize_sqlite_table_name(device_name)

    while not stop_event.is_set():
        cycle_start = time.time()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_packet = {"Timestamp": timestamp}
        successful_reads = 0
        best_packet = None
        best_non_zero_reads = -1
        active_profiles = []

        # Attempt to ensure connection is open
        if client is None or not client.is_socket_open():
            client = connect_modbus(host, port, device_name, timeout)

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
            elif best_packet is not None:
                data_packet.update(best_packet)

            if successful_reads == 0 or best_non_zero_reads == 0:
                logging.warning(f"[{device_name}] Connected but no non-zero telemetry was decoded - skipping write.")
                try:
                    client.close()
                except Exception:
                    pass
                client = None
            else:
                if postgres_table:
                    try:
                        insert_to_postgres(postgres_table, data_packet, timestamp)
                    except Exception as e:
                        logging.error(f"[{device_name}] DB insert error: {e}")

                try:
                    save_to_sqlite(sqlite_table, data_packet, DB_COLUMNS)
                except Exception as exc:
                    logging.error(f"[{device_name}] SQLite save error: {exc}")
        else:
            logging.warning(f"[{device_name}] Device offline - skipping write until a real read succeeds.")

        # Precise 1-second interval tracking
        elapsed = time.time() - cycle_start
        sleep_time = max(0, SLEEP_INTERVAL - elapsed)
        stop_event.wait(sleep_time)

def run_fetcher():
    logging.info("Starting background data fetcher...")
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

def stop_fetcher():
    stop_event.set()
    logging.info("Background fetcher stop signal sent.")
