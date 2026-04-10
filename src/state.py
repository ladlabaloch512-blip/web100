GLOBAL_STOP = False
TASK_QUEUE = []
ACTIVE_DRIVERS = []
HEADLESS_MODE = False

# Live Messenger State
MESSENGER_ALERTS = []
NEW_MESSAGES_EVENT = False

import os

# Configs
import json

CONFIG_FILE = "config.json"
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def update_status(profile_name, status):
    app_config[f"status_{profile_name}"] = status
    save_config(app_config)

app_config = load_config()

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", app_config.get("discord_webhook", "YOUR_DISCORD_WEBHOOK_HERE"))
BASE_PATH = app_config.get("profiles_dir", None)

CATEGORIES = [
    "Tools", "Furniture", "Household", "Garden", "Appliances", "Video Games", "Books, Movies & Music",
    "Bags & Luggage", "Women's clothing & shoes", "Men's clothing & shoes", "Jewelry & Accessories",
    "Health & beauty", "Pet Supplies", "Baby & kids", "Toys & Games", "Electronics & computers",
    "Mobile phones", "Bicycles", "Arts & Crafts", "Sports & Outdoors", "Auto parts",
    "Musical Instruments", "Antiques & Collectibles", "Garage Sale", "Miscellaneous"
]
CONDITIONS = ["New", "Used - Like New", "Used - Good", "Used - Fair"]
AVAILABILITY = ["List as Single Item", "List as In Stock"]

# Theme Colors
BG_APP = "#F1F5F9"
BG_PANEL = "#FFFFFF"
FG_TEXT = "#1E293B"
BTN_BLUE = "#3B82F6"
BTN_BLUE_HOVER = "#2563EB"
BTN_ORANGE = "#F59E0B"
BTN_ORANGE_HOVER = "#D97706"
BTN_GREEN = "#10B981"
BTN_GREEN_HOVER = "#059669"
BTN_RED = "#EF4444"
BTN_RED_HOVER = "#DC2626"
BTN_PURPLE = "#8B5CF6"
BTN_PURPLE_HOVER = "#7C3AED"
BORDER_COLOR = "#E2E8F0"
