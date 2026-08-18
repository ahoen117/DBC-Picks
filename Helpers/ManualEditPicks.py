import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path.cwd() / 'dbcPicks.db')
cur = conn.cursor()


# Deletes all rows from the pick table. Run This when playoffs start. Also delete from the picks data.json file afterwards.
cur.execute("DELETE FROM picks")

conn.commit()
conn.close()
print("Done!")