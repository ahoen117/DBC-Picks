import sqlite3
import json
from datetime import datetime
from pathlib import Path

def export_to_json(race_name="DARLINGTON", output_file="picks-data.json"):
    conn = sqlite3.connect(Path.cwd().parent / 'dbcPicks.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Players in your exact order
    players = ['David', 'Randy', 'Travis', 'Will', 'Aaron', 'Quentin', 'Taylor', 'Dakota', 'Tomas']

    players = sorted(players)

    print(players)

    # 2. All unique drivers (alphabetical)
    cur.execute("SELECT DISTINCT driver FROM picks ORDER BY driver")
    drivers = [row['driver'] for row in cur.fetchall()]

    # 3. Picks data (who picked what and is it current week?)
    cur.execute("SELECT player_name, driver, is_current_pick FROM picks")
    picks = {}
    for row in cur.fetchall():
        p = row['player_name']
        if p not in picks:
            picks[p] = {}
        picks[p][row['driver']] = bool(row['is_current_pick'])

    # 4. Points (total from your players table)
    cur.execute("SELECT player_name, total_points FROM players")
    total_points = {row['player_name']: row['total_points'] for row in cur.fetchall()}

    # Last Week Points — placeholder for now (you can add a column later if you want)
    # For now we'll just use 0 or pull from another table if you add it
    last_week_points = {p: 0 for p in players}   # ← change this later if you store last week points

    conn.close()

    data = {
        "race_name": race_name,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "players": players,
        "drivers": drivers,
        "picks": picks,
        "last_week_points": last_week_points,
        "total_points": total_points
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exported to {output_file} — ready for the website!")

if __name__ == "__main__":
    # Change the race name each week
    export_to_json("DARLINGTON")