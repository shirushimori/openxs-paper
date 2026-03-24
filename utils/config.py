import json
import os

CONFIG_PATH = "config/settings.json"


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}

    with open(CONFIG_PATH, "r") as f:
        content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)


def save_config(data):
    os.makedirs("config", exist_ok=True)

    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)
