import json
import sqlite3
from pathlib import Path

dbPath = Path.cwd()
dbPath = dbPath.parent

week = 7

conn = sqlite3.connect(dbPath / 'dbcPicks.db')
cur = conn.cursor()

cur.execute("DELETE FROM picks WHERE week = ?", (week,))

conn.commit()
conn.close()
print("Done!")