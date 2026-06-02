import json
import os
import uuid

CONFIG_FILE = "connections.json"

def get_config_path():
    # Store connections.json in the current working directory (workspace root)
    return os.path.abspath(CONFIG_FILE)

def reorder_profile_keys(profile):
    new_profile = {}
    if "id" in profile:
        new_profile["id"] = profile["id"]
    if "db_type" in profile:
        new_profile["db_type"] = profile["db_type"]
    else:
        new_profile["db_type"] = "PostgreSQL"
        
    for k, v in profile.items():
        if k not in ("id", "db_type"):
            new_profile[k] = v
    return new_profile

def load_profiles():
    path = get_config_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            profiles = json.load(f)
        
        # Migrate and reorder profiles
        migrated = False
        for i, p in enumerate(profiles):
            reordered = reorder_profile_keys(p)
            if list(p.keys()) != list(reordered.keys()) or p != reordered:
                profiles[i] = reordered
                migrated = True
                
        if migrated:
            save_profiles(profiles)
            
        return profiles
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
    
    # Ensure input profile has keys reordered
    profile = reorder_profile_keys(profile)
    
    if "id" not in profile or not profile["id"]:
        profile["id"] = str(uuid.uuid4())
        # Re-run reorder since id was just generated
        profile = reorder_profile_keys(profile)
        profiles.append(profile)
    else:
        # Find and update
        for i, p in enumerate(profiles):
            if p.get("id") == profile["id"]:
                profiles[i] = profile
                break
        else:
            profiles.append(profile)
            
    # Enforce order on all profiles in database
    for i, p in enumerate(profiles):
        profiles[i] = reorder_profile_keys(p)
        
    save_profiles(profiles)
    return profile

def delete_profile(profile_id):
    profiles = load_profiles()
    profiles = [p for p in profiles if p.get("id") != profile_id]
    save_profiles(profiles)

VERSION = "0.1.0"
