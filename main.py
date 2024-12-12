import requests
import json
import time
from datetime import datetime
import logging

class SteamMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.specials_url = "https://store.steampowered.com/api/featuredcategories"
        self.price_url = "https://store.steampowered.com/api/appdetails"
        self.free_games_file = "temp_free_games.json"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('steam_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_existing_games(self):
        try:
            with open(self.free_games_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            self.logger.error(f"Error reading {self.free_games_file}. File might be corrupted.")
            return []

    def check_game(self, app_id: int):
        params = {
            "appids": app_id,
            "cc": "us",
            "l": "en",
            "filters": "price_overview,basic"
        }
        
        try:
            response = self.session.get(self.price_url, params=params)
            response.raise_for_status()  # Raise exception for bad status codes
            
            data = response.json()
            if str(app_id) in data and data[str(app_id)]["success"]:
                game_data = data[str(app_id)]["data"]
                
                # Log full price data for debugging
                self.logger.debug(f"Price data for {app_id}: {json.dumps(game_data.get('price_overview', {}))}")
                
                # Check if game has price_overview
                if "price_overview" not in game_data:
                    self.logger.debug(f"No price_overview for game {app_id}")
                    return False
                
                price_data = game_data["price_overview"]
                
                # More detailed condition checking with logging
                if (not game_data.get("is_free", True) and  # not permanently free
                    price_data.get("initial", 0) > 0 and    # had initial price
                    price_data.get("discount_percent", 0) == 100):  # 100% discount
                    
                    return self.save_free_game(app_id, game_data)
                
            else:
                self.logger.debug(f"Failed to get data for game {app_id}")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error checking game {app_id}: {str(e)}")
        except KeyError as e:
            self.logger.error(f"Unexpected data structure for game {app_id}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error checking game {app_id}: {str(e)}")
        
        return False


    def save_free_game(self, app_id: int, game_data: dict):
        try:
            existing_games = self.load_existing_games()
            if not any(game["id"] == app_id for game in existing_games):
                price_overview = game_data["price_overview"]
                game_info = {
                    "id": app_id,
                    "name": game_data.get("name", "Unknown"),
                    "found_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "original_price": price_overview.get("initial_formatted", "Unknown"),
                    "end_date": datetime.fromtimestamp(price_overview.get("discount_end_date", 0)).strftime("%Y-%m-%d %H:%M:%S") if price_overview.get("discount_end_date") else "Unknown"
                }
                
                existing_games.append(game_info)
                with open(self.free_games_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_games, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"Found new temp free game: {game_info['name']} (was {game_info['original_price']}, free until {game_info['end_date']})")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error saving free game {app_id}: {str(e)}")
            return False

    def check_prices(self):
        try:
            response = self.session.get(self.specials_url)
            response.raise_for_status()
            
            data = response.json()
            if "specials" in data and "items" in data["specials"]:
                for item in data["specials"]["items"]:
                    self.check_game(item["id"])
                    time.sleep(1)  # Be nice to Steam's API
            else:
                self.logger.warning("Unexpected response structure from Steam API")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching specials: {str(e)}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing response: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error in check_prices: {str(e)}")

def main():
    monitor = SteamMonitor()
    while True:
        try:
            monitor.logger.info(f"Checking for 100% discounts at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            monitor.check_prices()
            time.sleep(3600)  # Wait for 1 hour
        except KeyboardInterrupt:
            monitor.logger.info("Monitoring stopped by user")
            break
        except Exception as e:
            monitor.logger.error(f"Error in main loop: {str(e)}")
            time.sleep(60)  # Wait a minute before retrying if there's an error

if __name__ == "__main__":
    main()