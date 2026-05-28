#import csv
import sqlite3
from pathlib import Path
import json

dbPath = Path.cwd()
# dbPath = dbPath.parent

conn = sqlite3.connect(dbPath / 'dbcPicks.db')
cur = conn.cursor()

with open('PlayerStats.json') as ps:
    playerStats = json.load(ps)

for player, data in playerStats.items():
    driver = data.get("pick")
    if not driver:
        print(f"Player {player} has no pick")
        continue

    cur.execute("SELECT COUNT(*) FROM drivers WHERE driver_name = ?", (driver,))
    driverCount = cur.fetchone()[0]
    if driverCount == 0:
        message = f"Check {player}: {driver} not on list or misspelled"
        print(message)
        continue

    cur.execute("""
       SELECT COUNT(*) FROM picks WHERE player_name = ? AND driver = ?
    """, (player, driver))

    count = cur.fetchone()[0]
    # print(count)

    if count > 0:
        cur.execute("SELECT week FROM picks WHERE player_name = ? AND driver = ?", (player, driver))
        week = cur.fetchone()[0]
        message = f"Player {player} has already picked {driver} in week {week}"
        print(message)

conn.close()
print("Finished checking picks!")