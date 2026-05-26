import requests
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from dbc_picks.scoring import (
    compute_week_results,
    extract_event_short_name,
    extract_positions_by_last_name,
)

#set True for testing, will reuse saved scoreboard.json and edit the _test db file. True will grab new scoreboard.json file using api and use the actual db. 
testing = False
#set variable to true if you want to have the program overwrite the dbcPicks.db.bak file with the current version of the db.
createBackup = True

#copy db to make a test.db file if testing is active. 
if testing == True:
    shutil.copy('dbcPicks.db', 'dbcPicks_test.db')

if createBackup == True:
    shutil.copy('dbcPicks.db', 'dbcPicks.db.bak')

def get_db_connection():
    if testing == True:
        conn = sqlite3.connect('dbcPicks_test.db')
    else:
        conn = sqlite3.connect('dbcPicks.db')
    conn.row_factory = sqlite3.Row   # makes rows behave like dicts (very convenient)
    return conn

def add_pick(player_name, driver, week=None, make_current=False):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM picks
        WHERE player_name = ? AND driver = ?
    """, (player_name, driver))

    if cur.fetchone()[0] > 0:
        conn.close()
        raise ValueError(f"{player_name} already picked {driver} this season")
    
    cur.execute("""
        INSERT INTO picks(player_name, driver, week, is_current_pick)
        VALUES(?,?,?,?)
    """, (player_name, driver, week, 1 if make_current else 0))


    conn.commit()
    conn.close()


def get_player_points(player_name):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT total_points FROM players WHERE player_name = ?", (player_name,))
    points_row = cur.fetchone()
    points = points_row['total_points'] if points_row else 0

    return points

def update_player_points(player_name, new_points):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE players 
        SET total_points = ? 
        WHERE player_name = ?
    """, (new_points, player_name))

    conn.commit()
    conn.close()

def get_standings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT player_name, total_points 
        FROM players 
        ORDER BY total_points DESC
    """)
    standings = [(row['player_name'], row['total_points']) for row in cur.fetchall()]
    conn.close()
    return standings

def get_week():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'current_week'")
    week = cur.fetchone()
    return week[0]

def incriment_week(current_week):
    conn = get_db_connection()
    cur = conn.cursor()
    new_week = current_week + 1
    cur.execute("UPDATE config SET value = ? WHERE key = 'current_week'", (new_week,))

    conn.commit()
    conn.close()

def updateWeeklyPoints(playerName, weeklyPoints):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE weeklyPoints SET weekly_points = ? WHERE player_name = ?", (weeklyPoints, playerName))

    conn.commit()
    conn.close()

def export_to_json(race_name, next_pick_order, output_file="Website/picks-data.json"):
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Players in your exact order
    cur.execute("SELECT DISTINCT player_name FROM picks")
    players = [row['player_name'] for row in cur.fetchall()]

    players = sorted(players)

    # 2. All unique drivers (alphabetical)
    cur.execute("SELECT DISTINCT driver_name FROM drivers ORDER BY driver_name")
    drivers = [row['driver_name'] for row in cur.fetchall()]

    # 3. Picks data (who picked what and is it current week?)
    cur.execute("SELECT player_name, driver, is_current_pick FROM picks")
    picks = {}
    for row in cur.fetchall():
        p = row['player_name']
        if p not in picks:
            picks[p] = {}
        picks[p][row['driver']] = bool(row['is_current_pick'])

    # 4. Points (total from your players table)
    cur.execute("SELECT player_name, total_points FROM players ORDER BY total_points DESC")
    total_points = [{"player": row[0], "points": row[1]} for row in cur.fetchall()]

    # Last Week Points — placeholder for now (you can add a column later if you want)
    # For now we'll just use 0 or pull from another table if you add it

    cur.execute("SELECT player_name, weekly_points FROM weeklyPoints ORDER BY weekly_points DESC")
    weekly_points = [{"player": row[0], "points": row[1]} for row in cur.fetchall()]


    conn.close()

    data = {
        "race_name": race_name,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "players": players,
        "drivers": drivers,
        "picks": picks,
        "total_points": total_points,
        "weekly_points": weekly_points,
        # next pick order = worst finish -> best finish (for next week drafting)
        "sorted_results": next_pick_order,
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exported to {output_file} — ready for the website!")


with open("PlayerStats.json") as ps:
    playerStats = json.load(ps)


if testing == False:
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard"

    response = requests.get(url)

    if response.status_code == 200:
        # 3. Parse the JSON response into a Python object (e.g., dictionary or list)
        json_data = response.json()
        
        # 4. Define the filename to save the data
        filename = 'scoreboard.json'
        
        # 5. Save the Python object to a JSON file
        with open(filename, 'w') as f:
            json.dump(json_data, f, indent=4)
else:
    with open('scoreboard.json', 'r') as f:
        json_data = json.load(f)

week = get_week()

players_to_picks = {person: playerStats[person]["pick"] for person in playerStats}

for person, pick_driver_last_name in players_to_picks.items():
    add_pick(person, pick_driver_last_name, week)

eventName = extract_event_short_name(json_data)
positions_by_last_name = extract_positions_by_last_name(json_data)
sortedResults, score_by_player, next_pick_order = compute_week_results(
    players_to_picks=players_to_picks,
    positions_by_last_name=positions_by_last_name,
)

incriment_week(week)

#create/edit text file to output to. 
with open("weeklyResults.txt", "w") as f:

    print(f"Weekly Results: {eventName}", file=f)
    print("-"*40, file=f)
    for player, pos in sortedResults:
        score = score_by_player[player]
        base_points = score.weekly_points - score.bonus_points

        # Print player name, their pick and the finishing position.
        print(f"{player}: {players_to_picks[player]} finished {pos}", file=f)

        # If 999 give reminder to check spelling.
        if pos == 999:
            print("Check for spelling errors in WeeklyPicks.csv...", file=f)

        oldPoints = get_player_points(player)

        totalPoints = oldPoints + score.total_week_points

        # Print base points (and separately print the winner bonus).
        print(f"You get {base_points} points", file=f)

        if score.bonus_points == 1:
            print("You get a bonus point for picking the race winner", file=f)

        update_player_points(player, totalPoints)
        updateWeeklyPoints(player, score.total_week_points)

        #blank line as seperator between players
        print("", file=f)

    print("Current Standings: ", file=f)

    #blank line as seperator between players
    print("-"*40, file=f)    

    for rank, (name, pts) in enumerate(get_standings(), 1):
        print(f"{rank}. {name}: {pts} pts", file=f)
    
    print("", file=f)
    print("Pick order for next week is: ", file=f)

    #blank line as seperator between players
    print("-"*40, file=f)

    for player in reversed(sortedResults):
        print(player[0], file=f)

export_to_json(eventName, next_pick_order)


