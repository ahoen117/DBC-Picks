#import csv
import sqlite3
from pathlib import Path

dbPath = Path.cwd()
dbPath = dbPath.parent

conn = sqlite3.connect(dbPath / 'dbcPicks_test.db')
cur = conn.cursor()

# with open('Driver_list.csv') as f:
#     reader = csv.reader(f, delimiter=',')

#     print(reader)

#     for row in reader:

#         cur.execute("INSERT INTO drivers(driver_name, car_number, team) VALUES (?, ?, ?)",
#                      (row[0], row[1], row[4],))

cur.execute("INSERT INTO players(player_name, total_points) VALUES (?, ?)", ("Test", 0))

#conn.commit()
conn.close()
print("Driver table updated!")