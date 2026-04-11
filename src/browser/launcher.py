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

import subprocess

def launch_browser(profile_name, base_path, state_module):
    global CACHED_DRIVER_PATH
    chrome_version = get_chrome_major_version()
    # Use the directory where the application is running from
    current_dir = os.getcwd()
    local_driver_path = os.path.join(current_dir, "chromedriver.exe")

    # We check if chromedriver.exe exists and matches the version.
    # To check version we can run `chromedriver.exe --version`
    download_needed = True
    if os.path.exists(local_driver_path):
        try:
            output = subprocess.check_output([local_driver_path, "--version"], stderr=subprocess.STDOUT, text=True)
            if f"ChromeDriver {chrome_version}" in output:
                download_needed = False
        except Exception:
            pass

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

    # Eager loading
    options.page_load_strategy = 'eager'

    # Disable Images/CSS (Optional for performance)
    if getattr(state_module, "DISABLE_IMAGES", False):
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2
        }
    else:
        prefs = {
            "profile.managed_default_content_settings.images": 1,
            "profile.managed_default_content_settings.stylesheets": 1
        }
    options.add_experimental_option("prefs", prefs)

    # Zero-storage and crashpad optimizations
    options.add_argument("--disk-cache-size=1")
    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-in-process-stack-traces")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")

    if getattr(state_module, "HEADLESS_MODE", False):
        options.add_argument("--headless=new")

    with driver_setup_lock:
        if download_needed:
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
