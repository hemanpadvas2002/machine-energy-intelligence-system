import sqlite3

DB = "machine_data.db"
conn = sqlite3.connect(DB)

cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print("Tables:", tables)

for t in tables:
    if t == "sqlite_sequence":
        continue
    count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    last  = conn.execute(f"SELECT timestamp FROM {t} ORDER BY timestamp DESC LIMIT 1").fetchone()
    last_ts = last[0] if last else "none"
    print(f"  {t:30s}: {count:5d} rows  |  last: {last_ts}")

conn.close()
