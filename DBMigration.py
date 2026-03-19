import json
import sqlite3

with open('PlayerStats.json') as f:
    data = json.load(f)

conn = sqlite3.connect('dbcPicks.db')
cur = conn.cursor()

# Insert players
for player, info in data.items():
    cur.execute("INSERT OR REPLACE INTO players (player_name, total_points) VALUES (?, ?)",
                (player, info['points']))

    # Insert historical chosen drivers
    for driver in info['chosen']:
        cur.execute("INSERT INTO picks (player_name, driver, is_current_pick) VALUES (?, ?, 0)",
                    (player, driver))

    # Insert current pick
    # if 'pick' in info and info['pick']:
    #     cur.execute("INSERT INTO picks (player_name, driver, is_current_pick) VALUES (?, ?, 1)",
    #                 (player, info['pick']))

conn.commit()
conn.close()
print("Migration done!")