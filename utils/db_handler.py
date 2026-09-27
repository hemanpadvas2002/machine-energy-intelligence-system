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

def sanitize_sqlite_table_name(name):
    return MACHINE_TABLE_MAPPING.get(name, name.lower().replace(" ", "_"))

def init_postgres_db():
    """Ensures all configured PostgreSQL machine tables exist."""
    conn = None
    try:
        conn = get_postgres_conn()
        cursor = conn.cursor()
        for table in MACHINE_TABLE_MAPPING.values():
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ({POSTGRES_MACHINE_TABLE_SCHEMA})"
            )
        conn.commit()
    except Exception as e:
        logger.warning(f"PostgreSQL init skipped: {e}")
    finally:
        if conn:
            conn.close()

def fetch_timestamp_range(table):
    """Fetches the min and max timestamp from a specific PostgreSQL table, with SQLite fallback."""
    conn = None
    try:
        conn = _get_postgres_conn_with_retry()
        cursor = conn.cursor()
        cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table}")
        result = cursor.fetchone()
        cursor.close()
        if result and result[0] is not None:
            return pd.Timestamp(result[0]), pd.Timestamp(result[1])
        return None, None
    except Exception as e:
        logger.warning(f"PostgreSQL bounds fetch failed for {table}, falling back to SQLite. Error: {e}")
        device_name = next((k for k, v in MACHINE_TABLE_MAPPING.items() if v == table), None)
        if device_name:
            sqlite_table = sanitize_sqlite_table_name(device_name)
            try:
                conn_sqlite = get_sqlite_conn()
                cursor_sq = conn_sqlite.cursor()
                cursor_sq.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {sqlite_table}")
                result = cursor_sq.fetchone()
                cursor_sq.close()
                if result and result[0] is not None:
                    return pd.Timestamp(result[0]), pd.Timestamp(result[1])
            except Exception as sq_exc:
                logger.warning("SQLite bounds fallback failed for %s: %s", sqlite_table, sq_exc)
            finally:
                if 'conn_sqlite' in locals() and conn_sqlite:
                    conn_sqlite.close()
        return None, None
    finally:
        if conn is not None and not conn.closed:
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
        logger.warning(f"PostgreSQL fetch failed for {table}, falling back to SQLite. Error: {e}")
        device_name = next((k for k, v in MACHINE_TABLE_MAPPING.items() if v == table), None)
        if device_name:
            sqlite_table = sanitize_sqlite_table_name(device_name)
            try:
                conn_sqlite = get_sqlite_conn()
                query = f"SELECT * FROM {sqlite_table} ORDER BY timestamp"
                df = pd.read_sql_query(query, conn_sqlite)
                if not df.empty:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
            except Exception as sq_exc:
                logger.error("SQLite fallback fetch error: %s", sq_exc)
            finally:
                if 'conn_sqlite' in locals() and conn_sqlite:
                    conn_sqlite.close()
        return pd.DataFrame()
    finally:
        if conn is not None and not conn.closed:
            conn.close()


def fetch_data_by_date_range(table, start_date, end_date):
    """Fetches data from a specific PostgreSQL table within a date range."""
    conn = None
    try:
        conn = _get_postgres_conn_with_retry()
        # Convert date to timestamp range [start_date 00:00:00, end_date 23:59:59]
        query = f"SELECT * FROM {table} WHERE timestamp >= %s AND timestamp <= %s ORDER BY timestamp"
        params = (
            f"{start_date} 00:00:00",
            f"{end_date} 23:59:59"
        )
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            
        return df
    except Exception as e:
        logger.warning(f"PostgreSQL range fetch failed for {table}. Error: {e}")
        # Fallback to SQLite
        device_name = next((k for k, v in MACHINE_TABLE_MAPPING.items() if v == table), None)
        if device_name:
            sqlite_table = sanitize_sqlite_table_name(device_name)
            try:
                conn_sqlite = get_sqlite_conn()
                # SQLite Date filtering
                query = f"SELECT * FROM {sqlite_table} WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp"
                df = pd.read_sql_query(query, conn_sqlite, params=(f"{start_date} 00:00:00", f"{end_date} 23:59:59"))
                if not df.empty:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
            except Exception as sq_exc:
                logger.error("SQLite range fallback fetch error: %s", sq_exc)
            finally:
                if 'conn_sqlite' in locals() and conn_sqlite:
                    conn_sqlite.close()
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
        logger.warning(f"PostgreSQL fetch failed for {table}, falling back to SQLite. Error: {exc}")
        device_name = next((k for k, v in MACHINE_TABLE_MAPPING.items() if v == table), None)
        if device_name:
            sqlite_table = sanitize_sqlite_table_name(device_name)
            try:
                conn_sqlite = get_sqlite_conn()
                query = f"""
                    SELECT timestamp, avg_voltage_ln, avg_voltage_ll, avg_current, total_kw, total_net_kwh
                    FROM {sqlite_table}
                    ORDER BY timestamp DESC
                    LIMIT {limit}
                """
                df = pd.read_sql_query(query, conn_sqlite)
                if not df.empty:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df = df.sort_values("timestamp").reset_index(drop=True)
                return df
            except Exception as sq_exc:
                logger.error("SQLite fallback recent fetch error: %s", sq_exc)
            finally:
                if 'conn_sqlite' in locals() and conn_sqlite:
                    conn_sqlite.close()
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
        logger.warning(f"PostgreSQL fetch failed for {table}, falling back to SQLite. Error: {exc}")
        device_name = next((k for k, v in MACHINE_TABLE_MAPPING.items() if v == table), None)
        if device_name:
            sqlite_table = sanitize_sqlite_table_name(device_name)
            try:
                conn_sqlite = get_sqlite_conn()
                query = f"""
                    SELECT timestamp, avg_voltage_ln, avg_voltage_ll, avg_current, total_kw, total_net_kwh
                    FROM {sqlite_table}
                    WHERE timestamp > ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                """
                df = pd.read_sql_query(query, conn_sqlite, params=(since_timestamp, limit))
                if not df.empty:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
            except Exception as sq_exc:
                logger.error("SQLite fallback incremental fetch error: %s", sq_exc)
            finally:
                if 'conn_sqlite' in locals() and conn_sqlite:
                    conn_sqlite.close()
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
        logger.warning(f"PostgreSQL snapshot fetch failed, falling back to SQLite. Error: {exc}")
        try:
            conn_sqlite = get_sqlite_conn()
            snapshots_sq = {}
            for machine_name, table in MACHINE_TABLE_MAPPING.items():
                sqlite_table = sanitize_sqlite_table_name(machine_name)
                query = f"""
                    SELECT timestamp, avg_voltage_ln, avg_voltage_ll, avg_current, total_kw, total_net_kwh
                    FROM {sqlite_table}
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                # Check if table exists first
                cursor = conn_sqlite.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{sqlite_table}';")
                if not cursor.fetchone():
                    continue
                    
                df = pd.read_sql_query(query, conn_sqlite)
                if df.empty:
                    continue
                row = df.iloc[0].to_dict()
                row["timestamp"] = pd.to_datetime(row["timestamp"])
                snapshots_sq[machine_name] = row
            return snapshots_sq
        except Exception as sq_exc:
            logger.error("SQLite fallback snapshot fetch error: %s", sq_exc)
            return {}
        finally:
            if 'conn_sqlite' in locals() and conn_sqlite:
                conn_sqlite.close()
    finally:
        if conn is not None and not conn.closed:
            conn.close()

def fetch_24h_peak_kw(table):
    """Returns MAX(ABS(total_kw)) recorded in the last 24 hours for the given table."""
    conn = None
    try:
        conn = _get_postgres_conn_with_retry()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT MAX(ABS(total_kw)) FROM {table} WHERE timestamp >= NOW() - INTERVAL '24 hours'"
        )
        result = cursor.fetchone()
        cursor.close()
        return float(result[0]) if result and result[0] is not None else 0.0
    except Exception as exc:
        logger.warning("Peak kW 24h fetch failed for %s (PostgreSQL): %s", table, exc)
        device_name = next((k for k, v in MACHINE_TABLE_MAPPING.items() if v == table), None)
        if device_name:
            sqlite_table = sanitize_sqlite_table_name(device_name)
            try:
                conn_sqlite = get_sqlite_conn()
                cursor_sq = conn_sqlite.cursor()
                cursor_sq.execute(
                    f"SELECT MAX(ABS(total_kw)) FROM {sqlite_table} WHERE timestamp >= datetime('now', '-24 hours')"
                )
                result = cursor_sq.fetchone()
                cursor_sq.close()
                return float(result[0]) if result and result[0] is not None else 0.0
            except Exception as sq_exc:
                logger.error("SQLite peak kW 24h fallback error: %s", sq_exc)
            finally:
                if 'conn_sqlite' in locals() and conn_sqlite:
                    conn_sqlite.close()
        return 0.0
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
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp      TEXT NOT NULL,
                avg_voltage_ln REAL,
                avg_voltage_ll REAL,
                avg_current    REAL,
                total_kw       REAL,
                total_net_kwh  REAL,
                state_label    TEXT,
                p_idle         REAL,
                p_working      REAL
            )
        """)
        for col, col_type in [("state_label", "TEXT"), ("p_idle", "REAL"), ("p_working", "REAL")]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except Exception:
                pass
    conn.commit()
    conn.close()

def save_to_sqlite(table, data, columns_mapping, state=None):
    """Saves a data packet to SQLite."""
    columns = ["timestamp"] + list(columns_mapping.values())
    values = [data["Timestamp"]] + [
        None if data.get(k) == "Error" else data.get(k)
        for k in columns_mapping.keys()
    ]
    if state:
        columns += ["state_label", "p_idle", "p_working"]
        values += [state["state_label"], state["p_idle"], state["p_working"]]
    placeholders = ", ".join(["?"] * len(columns))
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
