import requests
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

#set True for testing, will reuse saved scoreboard.json and edit the _test db file. True will grab new scoreboard.json file using api and use the actual db. 
testing = True
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

def export_to_json(race_name, output_file="Website/picks-data.json"):
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
    cur.execute("SELECT player_name, total_points FROM players")
    total_points = {row['player_name']: row['total_points'] for row in cur.fetchall()}

    # Last Week Points — placeholder for now (you can add a column later if you want)
    # For now we'll just use 0 or pull from another table if you add it

    cur.execute("SELECT player_name, weekly_points FROM weeklyPoints")
    weekly_points = {row['player_name']: row['weekly_points'] for row in cur.fetchall()}


    conn.close()

    data = {
        "race_name": race_name,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "players": players,
        "drivers": drivers,
        "picks": picks,
        "total_points": total_points,
        "weekly_points": weekly_points,
        "sorted_results": reversedResults,
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

for person in playerStats:
    #value is set to pick in weekly picks csv

    add_pick(person, playerStats[person]["pick"], week)

#setup basic format for weeklyResults dict
weeklyResults = {
    name: 0 for name in playerStats
}


#positions set to blank dictionary. 
positions = {}

eventName = json_data['events'][0]['shortName']

competitors = json_data['events'][0]['competitions'][0]['competitors']

#fill out positions dict with driver name and finishing position.
for competitor in competitors:
        #get full name and position
        full_name = competitor['athlete']['fullName']
        pos = int(competitor['order'])
        #last_parts is a list splitting the name by spaces
        last_parts = full_name.split()
        #get last name from end of list, or second to the end if ending in "Jr."
        last_name = last_parts[-1]
        if last_name == "Jr.":
            last_name = last_parts[-2]
        #edit positions dict to key=last_name and value=position
        positions[last_name] = pos

#set weeklyResults to their matched finishing position, if position doesn't exist, give position 999
for player in playerStats:
    weeklyResults[player] = positions.get(playerStats[player]["pick"], 999)

#sort the above by finishing position
sortedResults = sorted(weeklyResults.items(), key=lambda x: x[1])

#set weekly number of points 8 to first, 0 to last. We have 9 players.
points = 8

incriment_week(week)

#create/edit text file to output to. 
with open("weeklyResults.txt", "w") as f:

    print(f"Weekly Results: {eventName}", file=f)
    print("-"*40, file=f)
    for player, pos in sortedResults:
        #print player name, their pick and the finishing position
        print(f"{player}: {playerStats[player]["pick"]} finished {pos}", file=f)

        #if 999 give reminder to check spelling
        if pos == 999:
            print("Check for spelling errors in WeeklyPicks.csv...", file=f)

        oldPoints = get_player_points(player)

        updateWeeklyPoints(player, points)

        totalPoints = points + oldPoints
        
        #print points
        print(f"You get {points} points", file=f)

        #if you pick the winner you get extra point
        if pos == 1:
            print("You get a bonus point for picking the race winner", file=f)
            totalPoints += 1

        update_player_points(player, totalPoints)
        
        #adjust points each itteration
        points -= 1

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

reversedResults = [item[0] for item in sortedResults]
reversedResults.reverse()

export_to_json(eventName)


