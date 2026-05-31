import json
import os
import uuid

CONFIG_FILE = "connections.json"

def get_config_path():
    # Store connections.json in the current working directory (workspace root)
    return os.path.abspath(CONFIG_FILE)

def load_profiles():
    path = get_config_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading connection profiles: {e}")
        return []

def save_profiles(profiles):
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving connection profiles: {e}")
        return False

def add_or_update_profile(profile):
    profiles = load_profiles()
    if "id" not in profile or not profile["id"]:
        profile["id"] = str(uuid.uuid4())
        profiles.append(profile)
    else:
        # Find and update
        for i, p in enumerate(profiles):
            if p.get("id") == profile["id"]:
                profiles[i] = profile
                break
        else:
            profiles.append(profile)
    save_profiles(profiles)
    return profile

def delete_profile(profile_id):
    profiles = load_profiles()
    profiles = [p for p in profiles if p.get("id") != profile_id]
    save_profiles(profiles)
