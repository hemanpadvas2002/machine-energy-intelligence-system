# Database Configuration
POSTGRES_CONFIG = {
    "dbname": "machine_data",
    "user": "postgres",
    "password": "1234",
    "host": "127.0.0.1",
    "port": "5432"
}

SQLITE_DB_PATH = "machine_data.db"
SQLITE_DB = SQLITE_DB_PATH  # Backward compatibility

# Device Configuration
DEVICES = [
    {
        "name": "Galaxy_CNC",
        "host": "169.254.92.218",  # APIPA direct link (for isolated testing)
        # To switch to office LAN: change host to "192.168.1.182" and port to 522
        "port": 520,
        # Direct laptop<->converter link: converter self-assigned an APIPA
        # (169.254.x.x) address. Laptop must also be on 169.254.x.x / 255.255.0.0.
        # Known-good port only, to avoid hammering the single-slot gateway.
        "candidate_ports": [520],
        "timeout": 5,
        "read_retries": 3,
        "skip_invalid_packets": True,
        # Connection to 520 works; reads were failing on the single default
        # profile. Try the full matrix so the right register type / slave id /
        # word order is auto-discovered.
        "probe_profiles": [
            {"register_type": "input", "slave_id": 1, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "holding", "slave_id": 1, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "input", "slave_id": 2, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "holding", "slave_id": 2, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "input", "slave_id": 247, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "holding", "slave_id": 247, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "input", "slave_id": 1, "byteorder": "BIG", "wordorder": "BIG", "address_offset": 0},
            {"register_type": "holding", "slave_id": 1, "byteorder": "BIG", "wordorder": "BIG", "address_offset": 0},
            {"register_type": "input", "slave_id": 1, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 1},
            {"register_type": "holding", "slave_id": 1, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 1},
        ],
    },
    {
        "name": "LML_GRINDMASTER_CNC",
        "host": "192.168.1.184",
        "port": 524,
        "candidate_ports": [524],
        "timeout": 5,
        "read_retries": 3,
        "skip_invalid_packets": True,
        "probe_profiles": [
            {"register_type": "input", "slave_id": 1, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "holding", "slave_id": 1, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "input", "slave_id": 2, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "holding", "slave_id": 2, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "input", "slave_id": 247, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "holding", "slave_id": 247, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 0},
            {"register_type": "input", "slave_id": 1, "byteorder": "BIG", "wordorder": "BIG", "address_offset": 0},
            {"register_type": "holding", "slave_id": 1, "byteorder": "BIG", "wordorder": "BIG", "address_offset": 0},
            {"register_type": "input", "slave_id": 1, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 1},
            {"register_type": "holding", "slave_id": 1, "byteorder": "BIG", "wordorder": "LITTLE", "address_offset": 1},
        ],
    },
    {
        "name": "AGI_ROBO_CNC",
        "host": "192.168.1.186",
        "port": 526,
        "candidate_ports": [526],
    },
    {
        "name": "Ace_Vantage_CNC",
        "host": "192.168.1.183",
        "port": 523,
        "candidate_ports": [523],
    },
]
ACTIVE_MACHINE_NAMES = {device["name"] for device in DEVICES}

# Modbus and Polling Settings
REGISTER_MAPPING = {
    "Avg Voltage LN": 0x06,
    "Avg Voltage LL": 0x0E,
    "Avg Current":    0x16,
    "Total KW":       0x2A,
    "Total net kWh":  0x3A,
}

DB_COLUMNS = {
    "Avg Voltage LN": "avg_voltage_ln",
    "Avg Voltage LL": "avg_voltage_ll",
    "Avg Current":    "avg_current",
    "Total KW":       "total_kw",
    "Total net kWh":  "total_net_kwh",
}

MACHINE_TABLE_MAPPING = {
    "Galaxy_CNC":          "galaxy_cnc_data",
    "MTX_CNC":             "mtx_cnc_data",
    "LML_GRINDMASTER_CNC": "lml_grindmaster_cnc_data",
    "AGI_ROBO_CNC":        "agi_robo_data",
    "Ace_Vantage_CNC":     "ace_vantage_cnc_data",
}

SLAVE_ID = 1
SLEEP_INTERVAL = 1
CONNECT_TIMEOUT = 3
MAX_RETRY_WAIT = 60
HANDSHAKE_INTERVAL_SECONDS = 15
PORT_PROBE_INTERVAL_SECONDS = 30
