import sqlite3
from pathlib import Path
import json

windows = True if Path("C:/").exists() else False

dbPath = Path.cwd()

if windows == True:
    dbPath = dbPath.parent

conn = sqlite3.connect(dbPath / 'dbcPicks.db')
cur = conn.cursor()

# Deletes all rows from the pick table. Run This when playoffs start. Also delete from the picks data.json file afterwards.
cur.execute("DELETE FROM picks")

picksData = json.load(open(dbPath / 'Website' / 'picks-data.json', 'r'))

for i in picksData["picks"]:
    picksData["picks"][i] = {}

print(picksData["picks"])

with open(dbPath / 'Website' /  'picks-data.json', 'w') as f:
    json.dump(picksData, f, indent=4)

conn.commit()
conn.close()
print("Done!")