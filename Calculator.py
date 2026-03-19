import requests
import json
import sys
import sqlite3

def get_db_connection():
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

with open("PlayerStats.json") as ps:
    playerStats = json.load(ps)

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

for person in playerStats:
    #value is set to pick in weekly picks csv

    add_pick(person, playerStats[person]["pick"])

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

        totalPoints = points + oldPoints
        
        #print points
        print(f"You get {points} points", file=f)

        #if you pick the winner you get extra point
        if pos == 1:
            print("You get a bonus point for picking the race winner", file=f)
            totalPoints += 1

        print(f"Your total for the season is: {totalPoints} points", file=f)

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
    
    print("")
    print("Pick order for next week is: ", file=f)

    #blank line as seperator between players
    print("-"*40, file=f)

    for player in reversed(sortedResults):
        print(player[0], file=f)


