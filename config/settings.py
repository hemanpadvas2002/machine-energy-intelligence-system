# Database Configuration
POSTGRES_CONFIG = {
    "dbname": "machine_data",
    "user": "postgres",
    "password": "1234",
    "host": "127.0.0.1",
    "port": "5432"
}

SQLITE_DB = "machine_data.db"

# Device Configuration
DEVICES = [
    {"name": "Galaxy_CNC",         "host": "192.168.1.182", "port": 522},
    {"name": "MTX_CNC",            "host": "192.168.1.184", "port": 524},
    {
        "name": "LML_GRINDMASTER_CNC",
        "host": "192.168.1.185",
        "port": 525,
        "timeout": 5,
        "read_retries": 3,
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
    {"name": "AGI_ROBO_CNC",       "host": "192.168.1.186", "port": 526},
    {"name": "Ace_Vantage_CNC",    "host": "192.168.1.183", "port": 523},
]

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
