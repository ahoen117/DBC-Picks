import json
import sqlite3
from pathlib import Path

dbPath = Path.cwd()


week = 7

conn = sqlite3.connect(dbPath.parent / 'dbcPicks.db')
cur = conn.cursor()

cur.execute("DELETE FROM picks WHERE week = ?", (week,))

cur.execute(
    "UPDATE config SET value = ? WHERE key = ?",
    (7, "current_week")  # just a tuple of two elements, no extra parentheses
)

conn.commit()
conn.close()
print("Done!")