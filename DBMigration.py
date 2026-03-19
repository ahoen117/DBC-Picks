import csv
import sqlite3

conn = sqlite3.connect('dbcPicks.db')
cur = conn.cursor()

with open('Driver_list.csv') as f:
    reader = csv.reader(f, delimiter=',')

    print(reader)

    for row in reader:

        cur.execute("INSERT INTO drivers(driver_name, car_number, team) VALUES (?, ?, ?)",
                     (row[0], row[1], row[4],))


conn.commit()
conn.close()
print("Driver table updated!")