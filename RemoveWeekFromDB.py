import json
import sqlite3

conn = sqlite3.connect('dbcPicks.db')
cur = conn.cursor()

cur.execute("DELETE FROM picks WHERE week = 7")

conn.commit()
conn.close()
print("Done!")