import os
import sys
import json
import random
import hashlib
import subprocess
import winreg
import winsound
import time

def get_chrome_major_version():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return int(version.split('.')[0])
    except:
        return None

def force_kill_browser(driver, profile_name=None):
    try:
        pid = getattr(driver, "browser_pid", None)
        try:
            driver.quit()
        except:
            pass
        if pid:
            subprocess.run(f"taskkill /F /PID {pid} /T", shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    except:
        pass

    if profile_name and sys.platform == "win32":
        try:
            # Aggressively kill any lingering chrome or chromedriver processes that are tied to this profile's command line arguments
            wmic_cmd = f'wmic process where "name=\'chrome.exe\' and commandline like \'%{profile_name}%\'" call terminate'
            subprocess.run(wmic_cmd, shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

            wmic_driver_cmd = f'wmic process where "name=\'chromedriver.exe\' and commandline like \'%{profile_name}%\'" call terminate'
            subprocess.run(wmic_driver_cmd, shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except:
            pass

def force_delete_dir(dir_path):
    try:
        subprocess.run(f'rmdir /S /Q "{dir_path}"', shell=True, capture_output=True)
    except:
        pass

def get_or_create_fingerprint(profile_name, base_path):
    profile_dir = os.path.join(base_path, profile_name)
    os.makedirs(profile_dir, exist_ok=True)
    fp_file = os.path.join(profile_dir, "fingerprint.json")

    if os.path.exists(fp_file):
        try:
            with open(fp_file, "r") as f:
                return json.load(f)
        except:
            pass

    seed = int(hashlib.md5(profile_name.encode()).hexdigest(), 16)
    random.seed(seed)

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]
    resolutions = ["1920,1080", "1366,768", "1536,864", "1440,900", "1280,720"]

    fp = {"user_agent": random.choice(user_agents), "window_size": random.choice(resolutions)}
    random.seed()

    with open(fp_file, "w") as f:
        json.dump(fp, f)
    return fp

def smart_cleanup(profile_name, base_path):
    profile_dir = os.path.join(base_path, profile_name, "Default")
    if not os.path.exists(profile_dir):
        return
    junk_folders = [r"Cache", r"Code Cache", r"GPUCache", r"Service Worker\CacheStorage", r"Network\Cache"]
    for junk in junk_folders:
        path = os.path.join(profile_dir, junk)
        if os.path.exists(path):
            force_delete_dir(path)

def check_login_status(profile_name, base_path):
    cookie_path = os.path.join(base_path, profile_name, "Default", "Network", "Cookies")
    if os.path.exists(cookie_path):
        return os.path.getsize(cookie_path) / 1024 > 15
    return False

def play_success_sound():
    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except:
        pass
