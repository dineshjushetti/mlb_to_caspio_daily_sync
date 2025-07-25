import requests
from datetime import datetime
import time

# ===== CONFIGURATION =====
CASPIO_CLIENT_ID = "your_caspio_client_id"
CASPIO_CLIENT_SECRET = "your_caspio_client_secret"
CASPIO_TABLE_NAME = "MLB_Game_Stats"
CASPIO_DOMAIN = "https://c1.caspio.com"  # update if you're on a different Caspio bridge domain

# ===== MLB API =====
def fetch_mlb_games(date=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"
    response = requests.get(url)
    data = response.json()
    game_ids = []
    for date_info in data.get('dates', []):
        for game in date_info.get('games', []):
            game_ids.append(game['gamePk'])
    return game_ids

def fetch_game_stats(game_id):
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def extract_team_stats(boxscore):
    try:
        home = boxscore['teams']['home']
        away = boxscore['teams']['away']
        return {
            "game_id": boxscore.get("teams", {}).get("home", {}).get("team", {}).get("id", 0),
            "game_date": datetime.now().strftime('%Y-%m-%d'),
            "home_team": home['team']['name'],
            "away_team": away['team']['name'],
            "home_score": home['teamStats']['batting']['runs'],
            "away_score": away['teamStats']['batting']['runs'],
            "venue": "",  # not directly available in boxscore
            "status": "Final"
        }
    except Exception as e:
        print("Error extracting stats:", e)
        return None

# ===== CASPIO API =====
def get_caspio_token(client_id, client_secret):
    url = f"{CASPIO_DOMAIN}/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    response = requests.post(url, headers=headers, data=payload)
    return response.json().get("access_token")

def push_to_caspio(access_token, table_name, record):
    url = f"{CASPIO_DOMAIN}/rest/v2/tables/{table_name}/records"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json={"Records": [record]})
    return response.status_code, response.json()

def main():
    token = get_caspio_token(CASPIO_CLIENT_ID, CASPIO_CLIENT_SECRET)
    if not token:
        print("Failed to authenticate with Caspio.")
        return
    game_ids = fetch_mlb_games()
    print(f"Found {len(game_ids)} games.")
    for game_id in game_ids:
        stats = fetch_game_stats(game_id)
        if stats:
            record = extract_team_stats(stats)
            if record:
                status, response = push_to_caspio(token, CASPIO_TABLE_NAME, record)
                print(f"Pushed game {game_id}: Status {status} – {response}")
            else:
                print(f"Skipping game {game_id} due to parse error.")
        time.sleep(1)  # Respectful delay to avoid overwhelming API

if __name__ == "__main__":
    main()
