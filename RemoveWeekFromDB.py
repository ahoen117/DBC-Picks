import json
import sqlite3

week = 7

conn = sqlite3.connect('dbcPicks.db')
cur = conn.cursor()

cur.execute("DELETE FROM picks WHERE week = ?", (week,))

conn.commit()
conn.close()
print("Done!")