import sqlite3

# Connect to the database (creates the file if it doesn't exist)
conn = sqlite3.connect('dbcPicks.db')
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

cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value INTEGER)")

cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('current_week', 7)")

# Commit changes and close
conn.commit()
conn.close()

print("Database and tables created successfully!")