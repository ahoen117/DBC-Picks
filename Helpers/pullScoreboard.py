import requests
import json

url = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard"

response = requests.get(url)

if response.status_code == 200:
    # 3. Parse the JSON response into a Python object (e.g., dictionary or list)
    json_data = response.json()
    
    # 4. Define the filename to save the data
    filename = 'scoreboard_test.json'
    
    # 5. Save the Python object to a JSON file
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=4)

print("Done! File should be saved.")