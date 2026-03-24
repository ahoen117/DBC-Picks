import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path.cwd() / 'dbcPicks.db')
cur = conn.cursor()

cur.execute("SELECT DISTINCT driver_name FROM drivers")
drivers = cur.fetchall()


last_names = []

for (full_name,) in drivers:
    parts = full_name.split()

    if parts[-1] == "Jr.":
        last_name = parts[-2]  # second to last
    else:
        last_name = parts[-1]  # last word

    last_names.append(last_name)

last_names.sort()


cur.execute("DROP TABLE IF EXISTS drivers")
conn.commit()

cur.execute("""
    CREATE TABLE drivers (
        driver_name TEXT
    )
""")
conn.commit()

for driver in last_names:
    cur.execute(
        "INSERT INTO drivers (driver_name) VALUES (?)",
        (driver,)
    )

conn.commit()
conn.close()
print("Done!")