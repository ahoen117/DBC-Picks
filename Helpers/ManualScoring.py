import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path.cwd().parent / 'dbcPicks.db')
cur = conn.cursor()

player = "Aaron"
weeklyPoints = 3

cur.execute('SELECT total_points FROM players WHERE player_name = ?', (player,))

totalPoints = cur.fetchone()[0]

print(f"That player's previous total is {totalPoints}")

totalPoints += weeklyPoints

print(f"That player's new total is {totalPoints}")

userInput = input("Do you want to update the DB with the new value?").lower().strip()

if userInput in ("yes", "y"):
    cur.execute('UPDATE players SET total_points = ? WHERE player_name = ?', (totalPoints, player))
    conn.commit()
conn.close()