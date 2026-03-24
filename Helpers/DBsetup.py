import sqlite3
from pathlib import Path

dbPath = Path.cwd()
#dbPath = dbPath.parent

# Connect to the database (creates the file if it doesn't exist)
conn = sqlite3.connect(dbPath / 'dbcPicks.db')
cur = conn.cursor()

# # 1. Players table
# cur.execute('''
# CREATE TABLE IF NOT EXISTS players (
#     player_name TEXT PRIMARY KEY,
#     total_points INTEGER DEFAULT 0
# )
# ''')

# # 2. Picks table (main history + current pick)
# cur.execute('''
# CREATE TABLE IF NOT EXISTS picks (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     player_name TEXT NOT NULL,
#     driver TEXT NOT NULL,
#     week INTEGER,                   -- e.g. 1 = Daytona, 2 = Atlanta, etc.
#     is_current_pick BOOLEAN DEFAULT 0,
#     picked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (player_name) REFERENCES players(player_name)
# )
# ''')

# # 3. Optional: Drivers table (full roster for availability checks)
# cur.execute('''
# CREATE TABLE IF NOT EXISTS drivers (
#     driver_name TEXT PRIMARY KEY,
#     car_number TEXT,
#     team TEXT,
#     active BOOLEAN DEFAULT 1
# )
# ''')


players = ['David', 'Randy', 'Travis', 'Will', 'Aaron', 'Quentin', 'Taylor', 'Dakota', 'Tomas']

points = [22,13,28,33,17,42,27,38,34]

pIndex = 0

for player in players:
    cur.execute("INSERT OR REPLACE INTO weeklyPoints (player_name, weekly_points) VALUES (?,?)", (player, 0))


for player in players:
    point = points[pIndex]
    print(point)
    cur.execute("INSERT OR REPLACE INTO players (player_name, total_points) VALUES (?,?)", (player, point))
    pIndex += 1

# Commit changes and close
conn.commit()
conn.close()

print("Database and tables created successfully!")