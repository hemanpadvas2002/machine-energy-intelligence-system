import psycopg2
from datetime import datetime

try:
    conn = psycopg2.connect(
        dbname="machine_data",
        user="postgres",
        password="Phadvas@123",   # <-- your password
        host="localhost",
        port="5432"
    )

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO ace_vantage_cnc_data
        (timestamp, avg_voltage_ln, avg_voltage_ll, avg_current, total_kw, total_net_kwh)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        datetime.now(),
        231.5,
        401.2,
        11.2,
        6.3,
        1200.4
    ))

    conn.commit()

    cur.close()
    conn.close()

    print("✅ Insert from Python successful")

except Exception as e:
    print("❌ Error:", e)