import sqlite3
from pathlib import Path

dbPath = Path.cwd()
dbPath = dbPath.parent

# Connect to the database (creates the file if it doesn't exist)
conn = sqlite3.connect(dbPath / 'dbcPicks.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT driver, COUNT(*) AS pick_count FROM picks GROUP BY driver ORDER BY pick_count DESC, driver ASC")
counts = cur.fetchall()

cur.execute("SELECT COUNT(DISTINCT driver) FROM picks")
uniqueDrivers = cur.fetchone()[0]

for row in counts:
    print(f"{row['driver']:12} : {row['pick_count']} times")

print(f"There have been {uniqueDrivers} different drivers picked this season")