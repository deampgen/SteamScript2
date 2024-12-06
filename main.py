import requests
import json
import time
from datetime import datetime

class SteamMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.specials_url = "https://store.steampowered.com/api/featuredcategories"
        self.price_url = "https://store.steampowered.com/api/appdetails"
        self.free_games_file = "temp_free_games.json"

    def load_existing_games(self):
        try:
            with open(self.free_games_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def check_game(self, app_id: int):
        params = {
            "appids": app_id,
            "cc": "us",
            "l": "en",
            "filters": "price_overview,basic"
        }
        
        response = self.session.get(self.price_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if str(app_id) in data and data[str(app_id)]["success"]:
                game_data = data[str(app_id)]["data"]
                
                # Проверяем что игра платная, но сейчас со 100% скидкой
                price_data = game_data.get("price_overview", {})
                if (not game_data.get("is_free") and  # не бесплатная игра
                    price_data.get("initial", 0) > 0 and  # изначально стоила денег
                    price_data.get("discount_percent") == 100):  # скидка 100%
                    
                    return self.save_free_game(app_id, game_data)
        return False

    def save_free_game(self, app_id: int, game_data: dict):
        existing_games = self.load_existing_games()
        if not any(game["id"] == app_id for game in existing_games):
            game_info = {
                "id": app_id,
                "name": game_data.get("name"),
                "found_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "original_price": game_data["price_overview"]["initial_formatted"],
                "end_date": datetime.fromtimestamp(game_data["price_overview"]["discount_end_date"]).strftime("%Y-%m-%d %H:%M:%S") if "discount_end_date" in game_data["price_overview"] else "Unknown"
            }
            
            existing_games.append(game_info)
            with open(self.free_games_file, 'w', encoding='utf-8') as f:
                json.dump(existing_games, f, ensure_ascii=False, indent=2)
            print(f"Found new temp free game: {game_info['name']} (was {game_info['original_price']}, free until {game_info['end_date']})")
            return True
        return False

    def check_prices(self):
        response = self.session.get(self.specials_url)
        if response.status_code == 200:
            data = response.json()
            if "specials" in data and "items" in data["specials"]:
                for item in data["specials"]["items"]:
                    self.check_game(item["id"])
                    time.sleep(1)

def main():
    monitor = SteamMonitor()
    while True:
        print(f"\nChecking for 100% discounts at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        monitor.check_prices()
        time.sleep(3600)

if __name__ == "__main__":
    main()
