import os
import time
import shutil
import threading
from src.utils.system_utils import get_chrome_major_version, get_or_create_fingerprint

import undetected_chromedriver as uc
import undetected_chromedriver.patcher as uc_patcher

driver_setup_lock = threading.Lock()
browser_init_lock = threading.Lock()
CACHED_DRIVER_PATH = None

def launch_browser(profile_name, base_path, state_module):
    global CACHED_DRIVER_PATH
    chrome_version = get_chrome_major_version()
    current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    local_driver_path = os.path.join(current_dir, f"chromedriver_v{chrome_version}.exe")

    fp = get_or_create_fingerprint(profile_name, base_path)

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={os.path.join(base_path, profile_name)}")
    options.add_argument("--disable-notifications")
    options.add_argument("--hide-crash-restore-bubble")
    options.add_argument("--disable-features=RestoreSession")

    options.add_argument(f"--user-agent={fp['user_agent']}")
    options.add_argument(f"--window-size={fp['window_size']}")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    with driver_setup_lock:
        if not os.path.exists(local_driver_path):
            print(f"[SYSTEM] Fetching ChromeDriver v{chrome_version}...")
            patcher = uc_patcher.Patcher(version_main=chrome_version)
            patcher.auto()
            shutil.copy(patcher.executable_path, local_driver_path)
        CACHED_DRIVER_PATH = local_driver_path

    with browser_init_lock:
        print(f"[{profile_name}] Initializing browser engine safely...")
        try:
            driver = uc.Chrome(options=options, driver_executable_path=CACHED_DRIVER_PATH, version_main=chrome_version, use_subprocess=True)
            state_module.ACTIVE_DRIVERS.append(driver)
            time.sleep(1.5)
            return driver
        except Exception as e:
            raise Exception(f"Failed to connect to browser port. Error: {str(e).splitlines()[0]}")
