import csv
import requests
import json

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

weeklyPicks = {}

with open('WeeklyPicks.csv', newline='') as picks:
    reader = csv.reader(picks)
    for row in reader:
        if len(row) >=2:
            #key is set to name in weekly picks csv
            player = row[0].strip()
            #value is set to pick in weekly picks csv
            weeklyPicks[player] = row[1].strip()

#setup basic format for weeklyResults dict
weeklyResults = {
    name: 0 for name in weeklyPicks
}

#positions set to blank dictionary. 
positions = {}

competitors = json_data['events'][0]['competitions'][0]['competitors']

for competitor in competitors:
    if row:
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
for player, last_name in weeklyPicks.items():
    weeklyResults[player] = positions.get(last_name, 999)

#sort the above by finishing position
sortedResults = sorted(weeklyResults.items(), key=lambda x: x[1])

#set weekly number of points 8 to first, 0 to last. We have 9 players.
points = 8

#create/edit text file to output to. 
with open("weeklyResults.txt", "w") as f:

    print("Weekly Results:", file=f)
    print("-"*40, file=f)
    for player, pos in sortedResults:
        #print player name, their pick and the finishing position
        print(f"{player}: {weeklyPicks[player]} finished {pos}", file=f)

        #if 999 give reminder to check spelling
        if pos == 999:
            print("Check for spelling errors in WeeklyPicks.csv...", file=f)
        
        #print points
        print(f"You get {points} points", file=f)

        #if you pick the winner you get extra point
        if pos == 1:
            print("You get a bonus point for picking the race winner", file=f)

        #adjust points each itteration
        points -= 1
        
        #blank line as seperator between players
        print("", file=f)

    print("Pick order for next week is: ", file=f)
    print("-"*40, file=f)

    for player in reversed(sortedResults):
        print(player[0], file=f)


