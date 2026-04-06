import logging
import time
import psycopg2
import sqlite3
import pandas as pd
from config.settings import MACHINE_TABLE_MAPPING, POSTGRES_CONFIG, SQLITE_DB

logger = logging.getLogger(__name__)
POSTGRES_RETRY_ATTEMPTS = 5
POSTGRES_RETRY_DELAY_SECONDS = 1.5

POSTGRES_MACHINE_TABLE_SCHEMA = """
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    avg_voltage_ln FLOAT,
    avg_voltage_ll FLOAT,
    avg_current FLOAT,
    total_kw FLOAT,
    total_net_kwh FLOAT
"""

def get_postgres_conn():
    """Returns a connection to the PostgreSQL database."""
    return psycopg2.connect(
        dbname=POSTGRES_CONFIG["dbname"],
        user=POSTGRES_CONFIG["user"],
        password=POSTGRES_CONFIG["password"],
        host=POSTGRES_CONFIG["host"],
        port=POSTGRES_CONFIG["port"]
    )


def _get_postgres_conn_with_retry():
    last_error = None
    for attempt in range(POSTGRES_RETRY_ATTEMPTS):
        try:
            return get_postgres_conn()
        except psycopg2.OperationalError as exc:
            last_error = exc
            if attempt < POSTGRES_RETRY_ATTEMPTS - 1:
                time.sleep(POSTGRES_RETRY_DELAY_SECONDS)
    raise last_error

def get_sqlite_conn():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(SQLITE_DB)

def init_postgres_db():
    """Ensures all configured PostgreSQL machine tables exist."""
    conn = get_postgres_conn()
    cursor = conn.cursor()
    try:
        for table in MACHINE_TABLE_MAPPING.values():
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ({POSTGRES_MACHINE_TABLE_SCHEMA})"
            )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def fetch_data_from_postgres(table):
    """Fetches all data from a specific PostgreSQL table."""
    conn = None
    try:
        conn = _get_postgres_conn_with_retry()
        cursor = conn.cursor()
        query = f"SELECT * FROM {table} ORDER BY timestamp"
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=columns)
        cursor.close()
        conn.close()

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        return df
    except Exception as e:
        logger.error("PostgreSQL fetch error for %s: %s", table, e)
        return pd.DataFrame()
    finally:
        if conn is not None and not conn.closed:
            conn.close()


def fetch_recent_points_from_postgres(table, limit=120):
    """Fetches a recent sliding window of telemetry points."""
    conn = None
    try:
        conn = _get_postgres_conn_with_retry()
        query = f"""
            SELECT timestamp, avg_voltage_ln, avg_voltage_ll, avg_current, total_kw, total_net_kwh
            FROM {table}
            ORDER BY timestamp DESC
            LIMIT %s
        """
        df = pd.read_sql_query(query, conn, params=(limit,))
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    except Exception as exc:
        logger.error("PostgreSQL recent fetch error for %s: %s", table, exc)
        return pd.DataFrame()
    finally:
        if conn is not None and not conn.closed:
            conn.close()


def fetch_incremental_points_from_postgres(table, since_timestamp, limit=240):
    """Fetches only telemetry points newer than the provided timestamp."""
    conn = None
    try:
        conn = _get_postgres_conn_with_retry()
        query = f"""
            SELECT timestamp, avg_voltage_ln, avg_voltage_ll, avg_current, total_kw, total_net_kwh
            FROM {table}
            WHERE timestamp > %s
            ORDER BY timestamp ASC
            LIMIT %s
        """
        df = pd.read_sql_query(query, conn, params=(since_timestamp, limit))
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as exc:
        logger.error("PostgreSQL incremental fetch error for %s: %s", table, exc)
        return pd.DataFrame()
    finally:
        if conn is not None and not conn.closed:
            conn.close()


def fetch_latest_machine_snapshots():
    """Fetches the latest available record from each configured machine table."""
    conn = None
    snapshots = {}
    try:
        conn = _get_postgres_conn_with_retry()
        for machine_name, table in MACHINE_TABLE_MAPPING.items():
            query = f"""
                SELECT timestamp, avg_voltage_ln, avg_voltage_ll, avg_current, total_kw, total_net_kwh
                FROM {table}
                ORDER BY timestamp DESC
                LIMIT 1
            """
            df = pd.read_sql_query(query, conn)
            if df.empty:
                continue
            row = df.iloc[0].to_dict()
            row["timestamp"] = pd.to_datetime(row["timestamp"])
            snapshots[machine_name] = row
        return snapshots
    except Exception as exc:
        logger.error("PostgreSQL snapshot fetch error: %s", exc)
        return {}
    finally:
        if conn is not None and not conn.closed:
            conn.close()

def insert_to_postgres(table, data_packet, timestamp):
    """Inserts one record into a PostgreSQL table."""
    try:
        conn = get_postgres_conn()
        cursor = conn.cursor()

        insert_query = f"""
        INSERT INTO {table}
        (timestamp, avg_voltage_ln, avg_voltage_ll, avg_current, total_kw, total_net_kwh)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (
            timestamp,
            data_packet.get("Avg Voltage LN") if data_packet.get("Avg Voltage LN") != "Error" else None,
            data_packet.get("Avg Voltage LL") if data_packet.get("Avg Voltage LL") != "Error" else None,
            data_packet.get("Avg Current") if data_packet.get("Avg Current") != "Error" else None,
            data_packet.get("Total KW") if data_packet.get("Total KW") != "Error" else None,
            data_packet.get("Total net kWh") if data_packet.get("Total net kWh") != "Error" else None
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error("PostgreSQL insert error for %s: %s", table, e)
        return False

def init_sqlite_db(devices, mapping_func):
    """Initializes SQLite database tables."""
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    for device in devices:
        table = mapping_func(device["name"])
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                timestamp      TEXT,
                avg_voltage_ln REAL,
                avg_voltage_ll REAL,
                avg_current    REAL,
                total_kw       REAL,
                total_net_kwh  REAL
            )
        """)
    conn.commit()
    conn.close()

def save_to_sqlite(table, data, columns_mapping):
    """Saves a data packet to SQLite."""
    columns = ["timestamp"] + list(columns_mapping.values())
    placeholders = ", ".join(["?"] * len(columns))
    values = [data["Timestamp"]] + [
        None if data.get(k) == "Error" else data.get(k)
        for k in columns_mapping.keys()
    ]
    conn = get_sqlite_conn()
    try:
        conn.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
    except Exception as exc:
        logger.error("SQLite save failed for %s: %s", table, exc)
    finally:
        conn.close()
