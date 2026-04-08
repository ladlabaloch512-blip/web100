import time
import requests
import os
import sys
import winreg
import json
import threading
import random
import shutil
import hashlib
import subprocess
import winsound

# Required Library for image processing: pip install Pillow
try:
    from PIL import Image, ImageTk
except ImportError:
    print("[ERROR] Missing required library: Pillow. Please open CMD and run: pip install Pillow")
    sys.exit(1)

# Required Library for browser automation
try:
    import undetected_chromedriver as uc
    import undetected_chromedriver.patcher as uc_patcher
except ImportError:
    print("[ERROR] Missing required library: undetected-chromedriver. Please open CMD and run: pip install undetected-chromedriver")
    sys.exit(1)

from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tkinter import Tk, filedialog, Label, Entry, Button, Text, StringVar, ttk, Toplevel, simpledialog, Canvas, Frame, Scrollbar, Checkbutton, BooleanVar, Radiobutton, LEFT, RIGHT, Y, BOTH, X, BOTTOM, TOP

# ==========================================
# ⚙️ GLOBAL CONFIGURATION & FLAGS
# ==========================================
DISCORD_WEBHOOK = "YOUR_DISCORD_WEBHOOK_HERE"
BASE_PATH = r"C:\Work\Profiles"
if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH)

CATEGORIES = [
    "Tools", "Furniture", "Household", "Garden", "Appliances", "Video Games", "Books, Movies & Music",
    "Bags & Luggage", "Women's clothing & shoes", "Men's clothing & shoes", "Jewelry & Accessories",
    "Health & beauty", "Pet Supplies", "Baby & kids", "Toys & Games", "Electronics & computers",
    "Mobile phones", "Bicycles", "Arts & Crafts", "Sports & Outdoors", "Auto parts",
    "Musical Instruments", "Antiques & Collectibles", "Garage Sale", "Miscellaneous"
]
CONDITIONS = ["New", "Used - Like New", "Used - Good", "Used - Fair"]
AVAILABILITY = ["List as Single Item", "List as In Stock"]

# --- PREMIUM INDUSTRIAL THEME COLORS ---
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

driver_setup_lock = threading.Lock()
browser_init_lock = threading.Lock()
CACHED_DRIVER_PATH = None

# Global State
GLOBAL_STOP = False
TASK_QUEUE = []
ACTIVE_DRIVERS = []

# ==========================================
# 🎨 UI ENHANCEMENTS, ALERTS & SOUND
# ==========================================
class HoverButton(Button):
    def __init__(self, master, hover_color=None, **kw):
        Button.__init__(self, master=master, **kw)
        self.defaultBackground = self["bg"]
        self.hoverBackground = hover_color if hover_color else self.defaultBackground
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.hoverBackground

    def on_leave(self, e):
        self['bg'] = self.defaultBackground

def play_success_sound():
    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except:
        pass

def show_alert(parent, title, message, alert_type="info"):
    alert = Toplevel(parent)
    alert.title(title)
    alert.geometry("400x180")
    alert.configure(bg=BG_PANEL)
    alert.transient(parent)
    alert.grab_set()

    color = BTN_GREEN if alert_type == "success" else BTN_RED if alert_type == "error" else BTN_BLUE
    Frame(alert, bg=color, height=6).pack(fill=X, side=TOP)

    Label(alert, text=title, font=("Segoe UI", 12, "bold"), bg=BG_PANEL, fg=color).pack(pady=(15, 5))
    Label(alert, text=message, font=("Segoe UI", 10), bg=BG_PANEL, fg=FG_TEXT, wraplength=360, justify="center").pack(pady=5)
    HoverButton(alert, text="OK", command=alert.destroy, bg=color, hover_color=color, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", width=12, cursor="hand2").pack(pady=10)

    alert.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (180 // 2)
    alert.geometry(f"+{x}+{y}")
    parent.wait_window(alert)

# ==========================================
# 🔧 SYSTEM UTILITIES & GHOST PROCESS KILLER
# ==========================================
def get_chrome_major_version():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return int(version.split('.')[0])
    except:
        return None

def force_kill_browser(driver):
    try:
        pid = driver.browser_pid
        driver.quit()
        subprocess.run(f"taskkill /F /PID {pid} /T", shell=True, capture_output=True)
    except:
        pass

def force_delete_dir(dir_path):
    try:
        subprocess.run(f'rmdir /S /Q "{dir_path}"', shell=True, capture_output=True)
    except:
        pass

def human_type(element, text, fast=False):
    global GLOBAL_STOP
    safe_text = "".join(c for c in text if ord(c) <= 0xFFFF)

    if fast:
        if not GLOBAL_STOP:
            element.send_keys(safe_text)
        return

    for char in safe_text:
        if GLOBAL_STOP:
            return
        element.send_keys(char)
        time.sleep(random.uniform(0.005, 0.02))

def get_or_create_fingerprint(profile_name):
    profile_dir = os.path.join(BASE_PATH, profile_name)
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

def smart_cleanup(profile_name):
    profile_dir = os.path.join(BASE_PATH, profile_name, "Default")
    if not os.path.exists(profile_dir):
        return
    junk_folders = [r"Cache", r"Code Cache", r"GPUCache", r"Service Worker\CacheStorage", r"Network\Cache"]
    for junk in junk_folders:
        path = os.path.join(profile_dir, junk)
        if os.path.exists(path):
            force_delete_dir(path)

def check_login_status(profile_name):
    cookie_path = os.path.join(BASE_PATH, profile_name, "Default", "Network", "Cookies")
    if os.path.exists(cookie_path):
        return os.path.getsize(cookie_path) / 1024 > 15
    return False

def wait_for_page_load(driver, timeout=60):
    if GLOBAL_STOP:
        return
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        pass

def wait_and_find(driver, xpath, timeout=60):
    if GLOBAL_STOP:
        raise Exception("Stopped")
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))

def wait_and_click(driver, xpath, timeout=60):
    if GLOBAL_STOP:
        raise Exception("Stopped")
    element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    element.click()
    return element

def js_click(driver, xpath, timeout=60):
    element = wait_and_find(driver, xpath, timeout)
    driver.execute_script("arguments[0].click();", element)
    return element

# ==========================================
# 🌐 BROWSER LAUNCHER
# ==========================================
def launch_browser(profile_name):
    global CACHED_DRIVER_PATH
    chrome_version = get_chrome_major_version()
    current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    local_driver_path = os.path.join(current_dir, f"chromedriver_v{chrome_version}.exe")

    fp = get_or_create_fingerprint(profile_name)

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={os.path.join(BASE_PATH, profile_name)}")
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
            ACTIVE_DRIVERS.append(driver)
            time.sleep(1.5)
            return driver
        except Exception as e:
            raise Exception(f"Failed to connect to browser port. Error: {str(e).splitlines()[0]}")

# ==========================================
# 🤖 CORE AUTOMATION FUNCTIONS
# ==========================================
def perform_manual(driver, p_name, target_url):
    try:
        driver.get(target_url)
        print(f"[{p_name}] Browser opened manually.")
        while len(driver.window_handles) > 0:
            if GLOBAL_STOP:
                break
            time.sleep(2)
    except:
        pass

def perform_login(driver, email, password, p_name):
    driver.get("https://web.facebook.com")
    wait_for_page_load(driver)
    time.sleep(3)
    if GLOBAL_STOP:
        return False

    try:
        email_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "email")))
        print(f"[{p_name}] Logging in...")
        human_type(email_field, email)
        pass_field = driver.find_element(By.NAME, "pass")
        human_type(pass_field, password)
        if GLOBAL_STOP:
            return False
        pass_field.send_keys(Keys.ENTER)
        time.sleep(7)

        max_wait_time = 300
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            if GLOBAL_STOP:
                return False
            current_url = driver.current_url.lower()
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            except:
                body_text = ""

            if "suspended" in body_text or "checkpoint/disabled" in current_url:
                print(f"❌ [{p_name}] Account Suspended: {email}")
                return False
            if "login" in current_url and "incorrect" in body_text:
                print(f"❌ [{p_name}] Invalid credentials: {email}")
                return False
            if "checkpoint" in current_url or "two_step" in current_url:
                print(f"⚠️ [{p_name}] Captcha/2FA Required. Solve manually in browser...")
                time.sleep(5)
                continue
            if "login" not in current_url and "checkpoint" not in current_url:
                print(f"✅ [{p_name}] Login successful!")
                return True
            time.sleep(2)
        return False
    except:
        if "facebook.com" in driver.current_url and "login" not in driver.current_url.lower():
            print(f"✅ [{p_name}] Profile is already logged in!")
            return True
        else:
            print(f"❌ [{p_name}] Failed to load Facebook login page.")
            return False

def perform_listing(driver, details, p_name):
    try:
        print(f"[{p_name}] Constructing Marketplace Listing...")
        driver.get("https://web.facebook.com/marketplace/create/item")
        wait_for_page_load(driver)
        time.sleep(4)

        wait_and_find(driver, "//input[@type='file']").send_keys("\n".join(details['images']))
        time.sleep(5)

        human_type(wait_and_find(driver, "//label[@aria-label='Title']//input | //span[contains(text(), 'Title')]/following::input[1]"), details['title'])
        human_type(wait_and_find(driver, "//label[@aria-label='Price']//input | //span[contains(text(), 'Price')]/following::input[1]"), details['price'])

        wait_and_click(driver, "//label[@aria-label='Category'] | //span[contains(text(), 'Category')]/following::div[1]")
        time.sleep(1.5)
        js_click(driver, f'//span[text()="{details["category"]}"]')
        time.sleep(1)

        wait_and_click(driver, "//label[@aria-label='Condition'] | //span[contains(text(), 'Condition')]/following::div[1]")
        time.sleep(1.5)
        js_click(driver, f'//span[text()="{details["condition"]}"]')
        time.sleep(1)

        try:
            more_btn_xpath = "//span[contains(text(), 'More details') or contains(text(), 'More Details')] | //div[@role='button']//span[contains(text(), 'More details')]"
            more_btn = wait_and_find(driver, more_btn_xpath, timeout=5)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", more_btn)
            time.sleep(2)
        except:
            pass

        try:
            desc_box = wait_and_find(driver, "//label[@aria-label='Description']//textarea | //span[contains(text(), 'Description')]/following::textarea[1]", timeout=5)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", desc_box)
            human_type(desc_box, details['desc'], fast=True)
            time.sleep(1)
        except Exception as e:
            print(f"[{p_name}] Description field skipped: {e}")

        if details.get('availability') and details['availability'] != "List as Single Item":
            try:
                avail_box = wait_and_find(driver, "//label[@aria-label='Availability'] | //span[contains(text(), 'Availability')]/following::div[1]", timeout=5)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", avail_box)
                time.sleep(1)
                avail_box.click()
                time.sleep(1)
                js_click(driver, f'//span[text()="{details["availability"]}"]')
            except:
                pass

        if details.get('tags'):
            try:
                tag_box = wait_and_find(driver, "//label[@aria-label='Product tags']//textarea | //span[contains(text(), 'Product tags')]/following::textarea[1]", timeout=5)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tag_box)
                human_type(tag_box, details['tags'], fast=True)
                tag_box.send_keys(Keys.ENTER)
            except:
                pass

        location_to_type = ""
        if details.get('loc_type') == 'file' and details.get('loc_file'):
            try:
                with open(details['loc_file'], 'r') as f:
                    locs = [l.strip() for l in f.readlines() if l.strip()]
                location_to_type = random.choice(locs) if details.get('loc_random') else locs[0]
            except:
                pass
        else:
            location_to_type = details.get('location', '')

        if location_to_type:
            try:
                loc_box = wait_and_find(driver, "//label[@aria-label='Location']//input", timeout=5)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", loc_box)
                loc_box.send_keys(Keys.CONTROL + "a")
                loc_box.send_keys(Keys.BACKSPACE)
                human_type(loc_box, location_to_type)
                time.sleep(3)
                loc_box.send_keys(Keys.ARROW_DOWN)
                loc_box.send_keys(Keys.ENTER)
            except:
                pass

        if details.get('public_meetup'):
            try: js_click(driver, "//span[text()='Public meetup']", timeout=3)
            except: pass
        if details.get('door_pickup'):
            try: js_click(driver, "//span[text()='Door pickup']", timeout=3)
            except: pass

        time.sleep(2)
        if not GLOBAL_STOP:
            print(f"[{p_name}] Proceeding to Publish...")
            try:
                next_btn_xpath = "//div[@aria-label='Next'] | //span[text()='Next'] | //div[@role='button']//span[text()='Next']"
                next_btn = wait_and_find(driver, next_btn_xpath, timeout=10)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(4)
            except Exception as e:
                print(f"[{p_name}] Next button issue: {e}")

            try:
                publish_btn_xpath = "//div[@aria-label='Publish'] | //span[text()='Publish'] | //div[@role='button']//span[contains(text(), 'Publish')]"
                publish_btn = wait_and_find(driver, publish_btn_xpath, timeout=10)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", publish_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", publish_btn)

                print(f"✅ [{p_name}] Listing POSTED and PUBLISHED successfully!")
                time.sleep(10)
            except Exception as e:
                print(f"❌ [{p_name}] Failed to click Publish: {e}")
                time.sleep(15)

    except Exception as e:
        if not GLOBAL_STOP:
            print(f"❌ [{p_name}] Error during listing: {e}")
            time.sleep(15)

def monitor_messenger(driver, p_name):
    try:
        print(f"[{p_name}] Analyzing Inbox (Waiting for E2EE sync)...")
        driver.get("https://web.facebook.com/messages/")
        wait_for_page_load(driver)
        time.sleep(6)

        # Switch to Marketplace Folder
        try:
            print(f"[{p_name}] Switching to Marketplace folder...")
            market_folder_xpath = "//span[text()='Marketplace' and not(ancestor::div[@role='banner'])] | //div[@role='row']//span[text()='Marketplace']"
            market_folder = wait_and_find(driver, market_folder_xpath, timeout=5)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", market_folder)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", market_folder)
            time.sleep(4)
        except:
            print(f"[{p_name}] Could not auto-click Marketplace folder, checking current view...")

        print(f"[{p_name}] Ignoring 'Unread' filter button. Scanning for Blue Dot (Unread indicator) instead...")

        # === THE NO-RELOAD DYNAMIC LOOP (Prevents Filter Reset) ===
        processed_hrefs = set()

        while len(processed_hrefs) < 5:
            if GLOBAL_STOP: break

            # Fetch fresh links every iteration to avoid StaleElement Reference
            chat_links_xpath = "//div[@role='row']//a[@role='link'] | //div[@role='navigation']//a[@role='link']"
            chat_links = driver.find_elements(By.XPATH, chat_links_xpath)

            target_link = None
            target_name = "Unknown"
            target_href = None

            for link in chat_links:
                try:
                    href = link.get_attribute("href")
                    text_content = link.text.strip()

                    if not href or not text_content:
                        continue
                    if text_content.startswith("Marketplace") or text_content == "Archive" or "Requests" in text_content:
                        continue
                    if href in processed_hrefs:
                        continue # Skip already processed URLs

                    # Check for Blue Dot / Unread Indicator within this specific link
                    is_unread = False
                    try:
                        # Find inner elements that indicate unread status.
                        # Usually aria-label="Mark as read" means it's currently unread, or an element with text 'Unread'
                        # Or a specific span class / blue dot. We look for aria labels.
                        unread_indicators = link.find_elements(By.XPATH, ".//*[@aria-label='Mark as read'] | .//*[@aria-label='Unread']")
                        if len(unread_indicators) > 0:
                            is_unread = True
                        else:
                            # Also check if any element has 'Unread' text inside the row
                            # Or blue background elements... Facebook uses an aria-label most consistently.
                            if "unread" in link.get_attribute("innerHTML").lower():
                                is_unread = True
                    except:
                        pass

                    if not is_unread:
                        continue # Skip this chat because it is already read

                    target_link = link
                    target_href = href
                    target_name = text_content.split('\n')[0]
                    break # Found the absolute first unprocessed unread chat!
                except: pass

            if not target_link:
                print(f"✅ [{p_name}] No more unread chats detected in the list! All clear.")
                time.sleep(3)
                break

            try:
                # Click directly on the DOM element without reloading the page!
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_link)
                time.sleep(0.5)
                try: target_link.click()
                except: driver.execute_script("arguments[0].click();", target_link)

                processed_hrefs.add(target_href) # Mark as processed via Unique URL
                time.sleep(6) # Generous wait for React to load the chat bubbles in the right pane

                print(f"\n--- [{p_name} INBOX: {target_name}] ---")

                # === SMART MESSAGE EXTRACTION ===
                try:
                    msg_nodes = driver.find_elements(By.XPATH, "//div[@role='main']//div[@role='grid']//div[@dir='auto']")
                    if not msg_nodes:
                        msg_nodes = driver.find_elements(By.XPATH, "//div[@role='main']//div[@dir='auto']")

                    lines = []
                    for node in msg_nodes:
                        try:
                            lines.extend([l.strip() for l in node.text.split('\n') if l.strip()])
                        except: pass

                    junk_blacklist = [
                        "choose a sticker", "type a message", "end-to-end encrypted", "marketplace",
                        "search", "customize chat", "chat members", "media, files and links", "privacy & support",
                        "send a quick response", "tap a response", "yes, are you interested", "yes, are you interested?",
                        "in talks. i'll let you know", "sorry, it's not available", "view buyer profile", "more options",
                        "started this chat", "sent you a message", "active", "seen", "send", "voice call", "video call",
                        "is this available?", "are you interested?"
                    ]

                    chat_history = []
                    for l in lines:
                        l_lower = l.lower()
                        if l == target_name or l == "You":
                            continue
                        if not any(j in l_lower for j in junk_blacklist) and len(l) > 1:
                            if l not in chat_history:
                                chat_history.append(l)

                    if chat_history:
                        print("💬 Last Messages in Chat:")
                        for msg in chat_history[-5:]:
                            print(f"   -> {msg}")
                    else:
                        print("💬 [No text messages found. Client might have used a button or sent an image.]")
                except Exception as history_error:
                    print(f"⚠️ [Could not load chat history: {history_error}]")

                print(f"🔔 ACTION REQUIRED IN TERMINAL FOR {p_name}!")
                reply = input(f"Type your reply to {target_name} (Press Enter to skip): ")

                if reply and not GLOBAL_STOP:
                    msg_box = wait_and_find(driver, "//div[@role='textbox']", timeout=5)
                    human_type(msg_box, reply, fast=True)
                    time.sleep(0.5)
                    msg_box.send_keys(Keys.ENTER)
                    print(f"✅ [{p_name}] Message delivered!")
                    time.sleep(3) # Wait for message to send before moving to next chat

            except Exception as inner_e:
                print(f"⚠️ [{p_name}] Skipped chat due to error: {inner_e}")
                continue

    except Exception as e:
        print(f"❌ [{p_name}] Inbox monitoring failed: {e}")

# ==========================================
# 🔄 MULTITHREADING WORKER & QUEUE RUNNER
# ==========================================
def worker_task(p_name, task_type, details=None, email=None, pwd=None, progress_callback=None):
    if GLOBAL_STOP:
        return
    print(f"\n🚀 Engaging profile: {p_name}")
    driver = None
    try:
        driver = launch_browser(p_name)
        if task_type == "login":
            perform_login(driver, email, pwd, p_name)
        elif task_type == "listing":
            perform_listing(driver, details, p_name)
        elif task_type == "messenger":
            monitor_messenger(driver, p_name)
        elif task_type == "manual":
            perform_manual(driver, p_name, details.get("url", "https://web.facebook.com"))
    except Exception as e:
        if not GLOBAL_STOP:
            print(f"❌ CRITICAL ERROR on {p_name}: {e}")
    finally:
        if driver:
            if task_type == "login" and check_login_status(p_name):
                time.sleep(10)
            force_kill_browser(driver)
            if driver in ACTIVE_DRIVERS:
                ACTIVE_DRIVERS.remove(driver)

        smart_cleanup(p_name)
        if progress_callback:
            progress_callback()

def execute_queue_automated(threads, root_window, progress_bar, update_ui_callback):
    global GLOBAL_STOP, TASK_QUEUE
    GLOBAL_STOP = False
    total_tasks = len(TASK_QUEUE)

    if total_tasks == 0:
        return

    completed = 0
    def update_progress():
        nonlocal completed
        completed += 1
        root_window.after(0, lambda: progress_bar.config(value=(completed/total_tasks)*100))

    print(f"\n[QUEUE] Dispatching {total_tasks} operations via {threads} threads...\n")
    with ThreadPoolExecutor(max_workers=threads) as executor:
        for task in TASK_QUEUE:
            if GLOBAL_STOP:
                break
            executor.submit(worker_task, task[0], task[1], task[2], task[3], task[4], update_progress)

    if not GLOBAL_STOP:
        play_success_sound()
        root_window.after(0, lambda: show_alert(root_window, "Execution Complete", "All queued tasks finished successfully!", "success"))
    else:
        root_window.after(0, lambda: show_alert(root_window, "Process Halted", "Execution stopped forcefully.", "error"))

    TASK_QUEUE.clear()
    root_window.after(0, lambda: progress_bar.config(value=0))
    root_window.after(0, update_ui_callback)

# ==========================================
# 🖥️ ADVANCED INDUSTRIAL DASHBOARD UI
# ==========================================
class ControlPanel:
    def __init__(self):
        self.root = Tk()
        self.root.title("Abiz Global - Enterprise Industrial Dashboard")
        self.root.geometry("1050x750")
        self.root.configure(bg=BG_APP)
        self.profile_vars = {}

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", font=("Segoe UI", 10), padding=6, relief="flat", background=BG_PANEL)
        style.configure("TProgressbar", thickness=10, background=BTN_GREEN)
        style.configure("TNotebook", background=BG_APP, borderwidth=0)
        style.configure("TNotebook.Tab", background="#E2E8F0", foreground=FG_TEXT, padding=10, font=("Segoe UI", 9))
        style.map("TNotebook.Tab", background=[("selected", BG_PANEL)], foreground=[("selected", BTN_BLUE)])

        header = Frame(self.root, bg=BG_PANEL, height=80, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill=X, side=TOP)
        Label(header, text="ABIZ GLOBAL ENTERPRISE", font=("Segoe UI", 22, "bold"), fg=BTN_BLUE, bg=BG_PANEL).pack(pady=15)

        main_layout = Frame(self.root, bg=BG_APP)
        main_layout.pack(fill=BOTH, expand=True, padx=25, pady=(15,0))

        # --- LEFT PANE ---
        left_pane = Frame(main_layout, bg=BG_APP, width=320)
        left_pane.pack(side=LEFT, fill=Y, padx=(0, 20))

        bulk_auto_frame = Frame(left_pane, bg=BG_PANEL, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        bulk_auto_frame.pack(fill=X, pady=(0, 20))
        Label(bulk_auto_frame, text="⚙️ AUTOMATION (MULTI)", font=("Segoe UI", 12, "bold"), fg=FG_TEXT, bg=BG_PANEL).pack(pady=(15,10))

        HoverButton(bulk_auto_frame, text="▶ Queued Manual Launch", hover_color=BTN_GREEN_HOVER, command=self.prepare_manual_queued, bg=BTN_GREEN, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=6)
        HoverButton(bulk_auto_frame, text="🔑 Queued Multi-Login", hover_color=BTN_BLUE_HOVER, command=self.prepare_login_queued, bg=BTN_BLUE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=6)
        HoverButton(bulk_auto_frame, text="🛍️ Queued Multi-Listing", hover_color=BTN_ORANGE_HOVER, command=self.open_multi_listing_form, bg=BTN_ORANGE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=6)
        HoverButton(bulk_auto_frame, text="💬 Queued Messenger Inbox", hover_color=BTN_PURPLE_HOVER, command=self.prepare_messenger_queued, bg=BTN_PURPLE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=6)
        Label(bulk_auto_frame, text="", bg=BG_PANEL).pack()

        mgt_frame = Frame(left_pane, bg=BG_PANEL, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        mgt_frame.pack(fill=X)
        Label(mgt_frame, text="📂 PROFILE MANAGEMENT", font=("Segoe UI", 12, "bold"), fg=FG_TEXT, bg=BG_PANEL).pack(pady=(15,10))
        HoverButton(mgt_frame, text="➕ Create Profiles & Shortcuts", hover_color="#475569", command=self.bulk_create, bg="#64748B", fg="white", font=("Segoe UI", 10), relief="flat", cursor="hand2").pack(fill=X, padx=20, pady=5)
        HoverButton(mgt_frame, text="🧹 Clean Cache & Temp Data", hover_color="#6B7280", command=self.bulk_clear_cache, bg="#9CA3AF", fg="white", font=("Segoe UI", 10), relief="flat", cursor="hand2").pack(fill=X, padx=20, pady=5)
        HoverButton(mgt_frame, text="🗑️ Delete Profiles (Immediate)", hover_color=BTN_RED_HOVER, command=self.bulk_delete_immediate, bg=BTN_RED, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=10)
        Label(mgt_frame, text="", bg=BG_PANEL).pack()

        # --- RIGHT PANE ---
        right_pane = Frame(main_layout, bg=BG_APP)
        right_pane.pack(side=RIGHT, fill=BOTH, expand=True)

        scanner_frame = Frame(right_pane, bg=BG_PANEL, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        scanner_frame.pack(fill=BOTH, expand=True, pady=(0, 15))

        stf = Frame(scanner_frame, bg=BG_PANEL)
        stf.pack(fill=X, pady=10, padx=15)
        Label(stf, text="📋 PROFILE DIRECTORY (SCANNER)", font=("Segoe UI", 13, "bold"), fg=FG_TEXT, bg=BG_PANEL).pack(side=LEFT)
        HoverButton(stf, text="🔄 Refresh", hover_color="#CBD5E1", command=self.refresh_profiles, bg="#E2E8F0", fg=FG_TEXT, font=("Segoe UI", 9, "bold"), relief="flat", padx=10, cursor="hand2").pack(side=RIGHT, padx=(5,0))
        HoverButton(stf, text="Select All", hover_color="#CBD5E1", command=self.select_all, bg="#E2E8F0", fg=FG_TEXT, font=("Segoe UI", 9, "bold"), relief="flat", padx=10, cursor="hand2").pack(side=RIGHT)

        canvas_frame = Frame(scanner_frame, bg=BG_PANEL)
        canvas_frame.pack(fill=BOTH, expand=True, padx=15, pady=(0, 15))
        self.canvas = Canvas(canvas_frame, bg=BG_PANEL, highlightthickness=0)
        scrollbar = Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = Frame(self.canvas, bg=BG_PANEL)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        queue_frame = Frame(right_pane, bg=BG_PANEL, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        queue_frame.pack(fill=X)
        qtf = Frame(queue_frame, bg=BG_PANEL)
        qtf.pack(fill=X, padx=15, pady=5)
        Label(qtf, text="⚙️ TASK QUEUE (PENDING)", font=("Segoe UI", 12, "bold"), fg=FG_TEXT, bg=BG_PANEL).pack(side=LEFT)
        self.lbl_qcount = Label(qtf, text="0 tasks queued", font=("Segoe UI", 9), fg="#64748B", bg=BG_PANEL)
        self.lbl_qcount.pack(side=RIGHT)

        qbf = Frame(queue_frame, bg=BG_PANEL)
        qbf.pack(fill=X, padx=15, pady=10)
        HoverButton(qbf, text="🗑️ Clear Queue", hover_color="#475569", command=self.clear_queue_list, bg="#64748B", fg="white", font=("Segoe UI", 10), relief="flat", width=15).pack(side=LEFT, padx=(0,5))
        HoverButton(qbf, text="🛑 STOP ALL", hover_color=BTN_RED_HOVER, command=self.emergency_stop, bg=BTN_RED, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", width=15).pack(side=LEFT, padx=5)
        HoverButton(qbf, text="🚀 RUN MASTER QUEUE", hover_color=BTN_GREEN_HOVER, command=self.run_master_queue_automated, bg=BTN_GREEN, fg="white", font=("Segoe UI", 10, "bold"), relief="flat").pack(side=RIGHT, fill=X, expand=True, padx=(5,0))

        bottom_frame = Frame(self.root, bg=BG_APP)
        bottom_frame.pack(fill=X, side=BOTTOM, pady=10)
        self.progress = ttk.Progressbar(bottom_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill=X, padx=25)

        self.refresh_profiles()
        self.update_queue_display()

    def update_queue_display(self):
        self.lbl_qcount.config(text=f"{len(TASK_QUEUE)} automated tasks queued")

    def clear_queue_list(self):
        global TASK_QUEUE
        TASK_QUEUE.clear()
        self.update_queue_display()

    def emergency_stop(self):
        global GLOBAL_STOP, ACTIVE_DRIVERS
        GLOBAL_STOP = True
        print("\n[EMERGENCY] STOP ALL COMMAND RECEIVED. FORCIBLY TERMINATING DRIVERS...")
        for driver in ACTIVE_DRIVERS:
            force_kill_browser(driver)
        ACTIVE_DRIVERS.clear()
        show_alert(self.root, "Stopped", "Automation halted forcefully. Ghost processes killed.", "error")

    def refresh_profiles(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.profile_vars.clear()

        folders = [f for f in os.listdir(BASE_PATH) if os.path.isdir(os.path.join(BASE_PATH, f))]
        folders.sort(key=lambda x: int(x.replace('Profile ', '')) if 'Profile ' in x else 0)

        header_row = Frame(self.scrollable_frame, bg=BG_PANEL)
        header_row.pack(fill=X, pady=(0, 5))
        Label(header_row, text="", width=4, bg=BG_PANEL).pack(side=LEFT)
        Label(header_row, text="PROFILE NAME", font=("Segoe UI", 9, "bold"), fg="#64748B", bg=BG_PANEL, anchor="w", width=25).pack(side=LEFT)
        Label(header_row, text="STATUS", font=("Segoe UI", 9, "bold"), fg="#64748B", bg=BG_PANEL, anchor="w", width=15).pack(side=LEFT)
        Label(header_row, text="ACTIONS", font=("Segoe UI", 9, "bold"), fg="#64748B", bg=BG_PANEL, width=25).pack(side=LEFT)

        for p in folders:
            var = BooleanVar()
            self.profile_vars[p] = var
            row = Frame(self.scrollable_frame, bg=BG_PANEL)
            row.pack(fill=X, pady=2)

            Checkbutton(row, variable=var, bg=BG_PANEL).pack(side=LEFT, padx=(3,0))
            Label(row, text=p, font=("Segoe UI", 10), fg=FG_TEXT, bg=BG_PANEL, anchor="w", width=23).pack(side=LEFT, padx=5)

            logged_in = check_login_status(p)
            status_text = "🟢  Ready" if logged_in else "⚪  Offline"
            color = BTN_GREEN if logged_in else "#9CA3AF"
            Label(row, text=status_text, font=("Segoe UI", 9, "bold"), fg=color, bg=BG_PANEL, anchor="w", width=13).pack(side=LEFT, padx=5)

            btn_frame = Frame(row, bg=BG_PANEL)
            btn_frame.pack(side=LEFT)
            HoverButton(btn_frame, text="⚡ Launch", hover_color=BTN_GREEN_HOVER, command=lambda pn=p: self.run_single_immediate(pn, "manual"), bg=BTN_GREEN, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=8).pack(side=LEFT, padx=2)
            HoverButton(btn_frame, text="🔑 Login", hover_color=BTN_BLUE_HOVER, command=lambda pn=p: self.run_single_immediate(pn, "login_auto"), bg=BTN_BLUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=8).pack(side=LEFT, padx=2)

    def select_all(self):
        for var in self.profile_vars.values():
            var.set(True)

    def get_selected_profiles(self):
        selected = [p for p, var in self.profile_vars.items() if var.get()]
        if not selected:
            show_alert(self.root, "Selection Required", "Please select at least one profile via scanner checkboxes.", "error")
        return selected

    def ask_thread_count(self, num_tasks):
        if num_tasks == 1:
            return 1
        return simpledialog.askinteger("Concurrency Config", f"How many parallel threads for {num_tasks} tasks? (1-10):", minvalue=1, maxvalue=10, parent=self.root)

    def add_automated_to_queue(self, profiles, task_type, details=None):
        global TASK_QUEUE
        if task_type == "login_multi_automated":
            filepath = filedialog.askopenfilename(title="Select Accounts IDs Text File", filetypes=[("Text Files", "*.txt")], parent=self.root)
            if not filepath:
                return
            with open(filepath, "r") as f:
                ids = [line.strip().split(",") for line in f if "," in line]
            for i, p_name in enumerate(profiles):
                if i < len(ids):
                    TASK_QUEUE.append((p_name, "login", None, ids[i][0], ids[i][1]))
        else:
            for p in profiles:
                TASK_QUEUE.append((p, task_type, details, None, None))

        self.update_queue_display()
        show_alert(self.root, "Added to Queue", f"{len(profiles)} tasks added to pending automated queue.", "success")

    def run_single_immediate(self, p_name, task_type):
        if task_type == "manual":
            sf = Toplevel(self.root)
            sf.title("Manual Launch Configuration")
            sf.geometry("380x250")
            sf.configure(bg=BG_PANEL)
            Frame(sf, bg=BTN_GREEN, height=6).pack(fill=X, side=TOP)
            Label(sf, text="Configure Startup URL", font=("Segoe UI", 11, "bold"), bg=BG_PANEL, fg=FG_TEXT).pack(pady=15)

            target_var = StringVar(value="fb")
            Radiobutton(sf, text="Facebook Default", variable=target_var, value="fb", bg=BG_PANEL).pack(anchor="w", padx=40)
            Radiobutton(sf, text="Blank New Tab", variable=target_var, value="blank", bg=BG_PANEL).pack(anchor="w", padx=40)
            custom_frame = Frame(sf, bg=BG_PANEL)
            custom_frame.pack(anchor="w", padx=40, pady=5)
            Radiobutton(custom_frame, text="Custom URL:", variable=target_var, value="custom", bg=BG_PANEL).pack(side=LEFT)
            Entry(custom_frame, width=30).pack(side=LEFT)

            def launch_sf():
                t = target_var.get()
                sf.destroy()
                url = "https://web.facebook.com" if t == "fb" else "about:blank" if t == "blank" else custom_frame.winfo_children()[1].get()
                threading.Thread(target=worker_task, args=(p_name, "manual", {"url": url}), daemon=True).start()

            HoverButton(sf, text="Launch Immediately", command=launch_sf, bg=BTN_GREEN, hover_color=BTN_GREEN_HOVER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat").pack(pady=20)
            return

        elif task_type == "login_auto":
            ids_input = simpledialog.askstring("Credentials", f"Enter credentials for {p_name}\n(Format: email,password):", parent=self.root)
            if not ids_input or "," not in ids_input:
                return
            ids = ids_input.split(",")
            threading.Thread(target=worker_task, args=(p_name, "login", None, ids[0], ids[1]), daemon=True).start()
            return

    def prepare_manual_queued(self):
        selected = self.get_selected_profiles()
        if not selected:
            return

        sf = Toplevel(self.root)
        sf.title("Queued Manual Launch")
        sf.geometry("380x250")
        sf.configure(bg=BG_PANEL)
        Frame(sf, bg=BTN_GREEN, height=6).pack(fill=X, side=TOP)
        Label(sf, text="Configure Startup URL", font=("Segoe UI", 11, "bold"), bg=BG_PANEL, fg=FG_TEXT).pack(pady=15)

        target_var = StringVar(value="fb")
        Radiobutton(sf, text="Facebook Default", variable=target_var, value="fb", bg=BG_PANEL).pack(anchor="w", padx=40)
        Radiobutton(sf, text="Blank New Tab", variable=target_var, value="blank", bg=BG_PANEL).pack(anchor="w", padx=40)
        custom_frame = Frame(sf, bg=BG_PANEL)
        custom_frame.pack(anchor="w", padx=40, pady=5)
        Radiobutton(custom_frame, text="Custom URL:", variable=target_var, value="custom", bg=BG_PANEL).pack(side=LEFT)
        Entry(custom_frame, width=30).pack(side=LEFT)

        def queue_manual_launch():
            t = target_var.get()
            url = "https://web.facebook.com" if t == "fb" else "about:blank" if t == "blank" else custom_frame.winfo_children()[1].get()
            sf.destroy()
            self.add_automated_to_queue(selected, "manual", {"url": url})

        HoverButton(sf, text="Add to Queue", command=queue_manual_launch, bg=BTN_GREEN, hover_color=BTN_GREEN_HOVER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat").pack(pady=20)

    def prepare_login_queued(self):
        selected = self.get_selected_profiles()
        if not selected:
            return
        self.add_automated_to_queue(selected, "login_multi_automated")

    def prepare_messenger_queued(self):
        selected = self.get_selected_profiles()
        if not selected:
            return
        self.add_automated_to_queue(selected, "messenger")

    def run_master_queue_automated(self):
        if not TASK_QUEUE:
            show_alert(self.root, "Queue Empty", "Add tasks to the queue first before running.", "error")
            return

        threads = self.ask_thread_count(len(TASK_QUEUE))
        if not threads:
            return
        threading.Thread(target=execute_queue_automated, args=(threads, self.root, self.progress, self.update_queue_display), daemon=True).start()

    def bulk_create(self):
        count = simpledialog.askinteger("Create Profiles", "How many new profiles to provision?", minvalue=1, parent=self.root)
        if not count:
            return
        chrome_exe = simpledialog.askstring("Chrome Path", "Provide path to Chrome.exe executable:", parent=self.root)
        if not chrome_exe:
            return
        shortcut_dir = filedialog.askdirectory(title="Select Destination Folder for Shortcuts", parent=self.root)
        if not shortcut_dir:
            return

        existing = len([f for f in os.listdir(BASE_PATH) if os.path.isdir(os.path.join(BASE_PATH, f))])
        for i in range(count):
            p_name = f"Profile {existing + i + 1}"
            p_path = os.path.join(BASE_PATH, p_name)
            os.makedirs(p_path, exist_ok=True)
            vbs_path = os.path.join(BASE_PATH, "temp.vbs")
            lnk_path = os.path.normpath(os.path.join(shortcut_dir, f"{p_name}.lnk"))
            vbs_code = f'Set oWS = WScript.CreateObject("WScript.Shell")\nSet oLink = oWS.CreateShortcut("{lnk_path}")\noLink.TargetPath = "{os.path.normpath(chrome_exe)}"\noLink.Arguments = "--user-data-dir=" & Chr(34) & "{os.path.normpath(p_path)}" & Chr(34)\noLink.Save'

            with open(vbs_path, "w") as f:
                f.write(vbs_code)
            subprocess.run(["cscript", "//nologo", vbs_path], shell=True)
            os.remove(vbs_path)
            get_or_create_fingerprint(p_name)

        self.refresh_profiles()
        play_success_sound()
        show_alert(self.root, "Success", f"Provisioned {count} Profiles and Shortcuts.", "success")

    def bulk_delete_immediate(self):
        selected = self.get_selected_profiles()
        if not selected:
            return

        alert_box = Toplevel(self.root)
        alert_box.title("Confirm Termination")
        alert_box.geometry("400x150")
        alert_box.configure(bg=BG_PANEL)
        alert_box.transient(self.root)
        alert_box.grab_set()

        Frame(alert_box, bg=BTN_RED, height=6).pack(fill=X, side=TOP)
        Label(alert_box, text="Confirm Termination", font=("Segoe UI", 12, "bold"), bg=BG_PANEL, fg=BTN_RED).pack(pady=(15, 5))
        Label(alert_box, text=f"Forcibly terminate {len(selected)} selected profiles permanently?", font=("Segoe UI", 10), bg=BG_PANEL, fg=FG_TEXT).pack(pady=5)

        def execute_delete():
            alert_box.destroy()
            print(f"\n[SYSTEM] Deleting {len(selected)} profiles securely...")
            total = len(selected)
            self.progress.config(value=0)
            for i, p_name in enumerate(selected):
                force_delete_dir(os.path.join(BASE_PATH, p_name))
                self.progress.config(value=((i+1)/total)*100)
            self.refresh_profiles()
            self.progress.config(value=0)
            play_success_sound()
            show_alert(self.root, "Profiles Deleted", "Profiles removed securely from disk.", "success")

        btn_frame = Frame(alert_box, bg=BG_PANEL)
        btn_frame.pack(pady=10)
        HoverButton(btn_frame, text="Yes, Terminate", command=execute_delete, bg=BTN_RED, hover_color=BTN_RED_HOVER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2").pack(side=LEFT, padx=10)
        HoverButton(btn_frame, text="Cancel", command=alert_box.destroy, bg="#E2E8F0", hover_color="#CBD5E1", fg=FG_TEXT, font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2").pack(side=LEFT, padx=10)

    def bulk_clear_cache(self):
        selected = self.get_selected_profiles()
        if not selected:
            return
        for p in selected:
            smart_cleanup(p)
        show_alert(self.root, "Cleaned", "Cache cleared. Logins are safe.", "success")

    def open_multi_listing_form(self):
        selected = self.get_selected_profiles()
        if not selected:
            return

        self.form = Toplevel(self.root)
        self.form.title("Queued Listing Deployment Configurator")
        self.form.geometry("550x780")
        self.form.configure(bg=BG_APP)
        Frame(self.form, bg=BTN_ORANGE, height=6).pack(fill=X, side=TOP)

        notebook = ttk.Notebook(self.form)
        notebook.pack(fill=BOTH, expand=True, padx=15, pady=15)

        tab1 = Frame(notebook, bg=BG_PANEL)
        notebook.add(tab1, text=" Basic Configuration ")
        tab2 = Frame(notebook, bg=BG_PANEL)
        notebook.add(tab2, text=" Taxonomy & Description ")
        tab3 = Frame(notebook, bg=BG_PANEL)
        notebook.add(tab3, text=" Settings & Deploy ")

        # Tab 1
        Label(tab1, text="Product Title:", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15,0), padx=15)
        self.title_ent = Entry(tab1, width=60, font=("Segoe UI", 10))
        self.title_ent.pack(padx=15, pady=5)

        Label(tab1, text="Product Price:", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(10,0))
        self.price_ent = Entry(tab1, width=60, font=("Segoe UI", 10))
        self.price_ent.pack(padx=15, pady=5)

        Label(tab1, text="Product Visual Assets (Multiple Images):", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15,0), padx=15)

        img_actions_frame = Frame(tab1, bg=BG_PANEL)
        img_actions_frame.pack(fill=X, padx=15)
        HoverButton(img_actions_frame, text="+ Add Image Files", hover_color="#F1F5F9", command=self.pick_multi_images, bg=BG_PANEL, fg=BTN_BLUE, font=("Segoe UI", 9, "bold"), relief="solid", bd=1, padx=10, cursor="hand2").pack(side=LEFT, pady=10)
        HoverButton(img_actions_frame, text="Clear All", hover_color="#FEF2F2", command=self.clear_all_images, bg=BG_PANEL, fg=BTN_RED, font=("Segoe UI", 9), relief="solid", bd=1, padx=10).pack(side=RIGHT, pady=10)

        thumbs_canvas_frame = Frame(tab1, bg="#F1F5F9", bd=1, relief="solid")
        thumbs_canvas_frame.pack(fill=BOTH, expand=True, padx=15, pady=10)
        self.img_paths_list = []
        self.img_tk_references = {}

        self.thumbs_canvas = Canvas(thumbs_canvas_frame, bg="#F1F5F9", highlightthickness=0)
        self.thumbs_scrollbar = Scrollbar(thumbs_canvas_frame, orient="vertical", command=self.thumbs_canvas.yview)
        self.thumbs_frame = Frame(self.thumbs_canvas, bg="#F1F5F9")

        self.thumbs_frame.bind("<Configure>", lambda e: self.thumbs_canvas.configure(scrollregion=self.thumbs_canvas.bbox("all")))
        self.thumbs_canvas.create_window((0, 0), window=self.thumbs_frame, anchor="nw")
        self.thumbs_canvas.configure(yscrollcommand=self.thumbs_scrollbar.set)
        self.thumbs_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.thumbs_scrollbar.pack(side=RIGHT, fill=Y)

        # Tab 2
        Label(tab2, text="Marketplace Category:", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15,0), padx=15)
        self.cat_var = StringVar(tab2)
        self.cat_var.set(CATEGORIES[0])
        ttk.Combobox(tab2, textvariable=self.cat_var, values=CATEGORIES, state="readonly", width=58).pack(padx=15, pady=5)

        Label(tab2, text="Condition Status:", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(10,0))
        self.cond_var = StringVar(tab2)
        self.cond_var.set(CONDITIONS[0])
        ttk.Combobox(tab2, textvariable=self.cond_var, values=CONDITIONS, state="readonly", width=58).pack(padx=15, pady=5)

        Label(tab2, text="Listing Description:", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(10,0))
        self.desc_ent = Text(tab2, width=54, height=7, font=("Segoe UI", 10), bd=1, relief="solid", highlightcolor=BORDER_COLOR)
        self.desc_ent.pack(padx=15, pady=5)

        Label(tab2, text="Search Tags (Comma separated):", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(10,0))
        self.tags_ent = Entry(tab2, width=60, font=("Segoe UI", 10))
        self.tags_ent.pack(padx=15, pady=5)

        # Tab 3
        Label(tab3, text="Geographic Location Strategy:", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15,0), padx=15)
        self.loc_strategy = StringVar(value="manual")
        Radiobutton(tab3, text="Manual City Entry:", variable=self.loc_strategy, value="manual", bg=BG_PANEL, font=("Segoe UI", 10)).pack(anchor="w", padx=25, pady=(5,0))
        self.loc_ent = Entry(tab3, width=54, font=("Segoe UI", 10))
        self.loc_ent.pack(padx=25)

        Radiobutton(tab3, text="Auto-Randomize from list per profile", variable=self.loc_strategy, value="list", bg=BG_PANEL, font=("Segoe UI", 10)).pack(anchor="w", padx=25, pady=(10,0))

        list_loc_frame = Frame(tab3, bg=BG_PANEL)
        list_loc_frame.pack(fill=X, padx=25)
        HoverButton(list_loc_frame, text="Browse Locations Text File (.txt)", hover_color="#CBD5E1", command=self.pick_multi_listing_loc_file, bg="#E2E8F0", fg=FG_TEXT, font=("Segoe UI", 9), relief="solid", bd=1, padx=10, cursor="hand2").pack(side=LEFT, pady=5)

        self.lbl_loc_file_status = Label(list_loc_frame, text="Status: Manual Strategy Enabled", bg=BG_PANEL, fg=BTN_BLUE, font=("Segoe UI", 9))
        self.lbl_loc_file_status.pack(side=LEFT, padx=10)

        Label(tab3, text="Fulfillment Preferences:", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(20,0), padx=15)
        self.avail_var = StringVar(tab3)
        self.avail_var.set(AVAILABILITY[0])
        ttk.Combobox(tab3, textvariable=self.avail_var, values=AVAILABILITY, state="readonly", width=53).pack(padx=15, pady=5)

        self.meet_pub = BooleanVar()
        Checkbutton(tab3, text="Public Meetup", variable=self.meet_pub, bg=BG_PANEL, font=("Segoe UI", 10)).pack(anchor="w", padx=25)
        self.meet_door = BooleanVar()
        Checkbutton(tab3, text="Door Pickup", variable=self.meet_door, bg=BG_PANEL, font=("Segoe UI", 10)).pack(anchor="w", padx=25)

        Label(tab3, text="Templates Management:", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(25,0), padx=15)
        templ_frame = Frame(tab3, bg=BG_PANEL)
        templ_frame.pack(fill=X, pady=5, padx=15)
        HoverButton(templ_frame, text="📂 Load Config Template", command=self.load_listing_config_template, bg=BTN_PURPLE, hover_color=BTN_PURPLE_HOVER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2").pack(side=LEFT, expand=True, fill=X, padx=5)
        HoverButton(templ_frame, text="💾 Save Current Config", command=self.save_listing_config_template, bg=BTN_ORANGE, hover_color=BTN_ORANGE_HOVER, fg="white", font=("Segoe UI", 10), relief="flat", cursor="hand2").pack(side=RIGHT, expand=True, fill=X, padx=5)

        HoverButton(tab3, text="➕ ADD TO MULTI-DEPLOY QUEUE", bg=BTN_ORANGE, hover_color=BTN_ORANGE_HOVER, fg="white", font=("Segoe UI", 12, "bold"), height=2, cursor="hand2", command=lambda: self.commit_bulk_listing_task(selected)).pack(fill=X, padx=10, pady=20, side=BOTTOM)

    def pick_multi_listing_loc_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")], parent=self.form)
        if path:
            self.multi_listing_loc_file_path = path
            self.lbl_loc_file_status.config(text=f"List Loaded: {os.path.basename(path)}")
            self.loc_strategy.set("list")

    def pick_multi_images(self):
        paths = filedialog.askopenfilenames(parent=self.form)
        if paths:
            self.img_paths_list.extend(list(paths))
            self.refresh_image_panel()

    def clear_all_images(self):
        self.img_paths_list.clear()
        self.refresh_image_panel()

    def remove_single_image(self, index):
        self.img_paths_list.pop(index)
        self.refresh_image_panel()

    def refresh_image_panel(self):
        for widget in self.thumbs_frame.winfo_children():
            widget.destroy()
        self.img_tk_references.clear()

        if not self.img_paths_list:
            Label(self.thumbs_frame, text="0 Visual Assets Provided", bg="#F1F5F9", fg=BTN_RED, font=("Segoe UI", 10, "bold")).pack(pady=20, anchor="center")
            return

        for i, path in enumerate(self.img_paths_list):
            filename = os.path.basename(path)
            container = Frame(self.thumbs_frame, bg="#F1F5F9", bd=1, relief="flat")
            container.pack(fill=X, pady=2)

            try:
                pil_image = Image.open(path)
                pil_image.thumbnail((32, 32))
                tk_image = ImageTk.PhotoImage(pil_image)
                self.img_tk_references[i] = tk_image
                Label(container, image=tk_image, bg="#F1F5F9").pack(side=LEFT, padx=5)
            except Exception as e:
                Label(container, text="🖼️", bg="#F1F5F9", font=("Segoe UI", 12)).pack(side=LEFT, padx=5)

            Label(container, text=f"({i+1}) {filename}", font=("Segoe UI", 9), fg=FG_TEXT, bg="#F1F5F9", anchor="w").pack(side=LEFT, padx=5, expand=True, fill=X)
            HoverButton(container, text="✕", command=lambda idx=i: self.remove_single_image(idx), bg=BG_PANEL, hover_color="#FEF2F2", fg=BTN_RED, font=("Arial", 9, "bold"), relief="flat", padx=8, cursor="hand2").pack(side=RIGHT, padx=5)

    def save_listing_config_template(self):
        details = {
            "title": self.title_ent.get(), "price": self.price_ent.get(), "category": self.cat_var.get(), "condition": self.cond_var.get(),
            "avail": self.avail_var.get(), "desc": self.desc_ent.get("1.0", "end-1c"), "tags": self.tags_ent.get(), "loc_strat": self.loc_strategy.get(),
            "loc": self.loc_ent.get(), "loc_f": getattr(self, 'multi_listing_loc_file_path', ""), "meet_p": self.meet_pub.get(),
            "door_p": self.meet_door.get(), "imgs": self.img_paths_list
        }
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], parent=self.form)
        if path:
            with open(path, 'w') as f:
                json.dump(details, f)
            show_alert(self.form, "Saved", "Configuration deployed to file securely.", "success")

    def load_listing_config_template(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], parent=self.form)
        if path:
            with open(path, 'r') as f:
                details = json.load(f)
            self.title_ent.delete(0, 'end')
            self.title_ent.insert(0, details.get("title", ""))

            self.price_ent.delete(0, 'end')
            self.price_ent.insert(0, details.get("price", ""))

            self.cat_var.set(details.get("category", CATEGORIES[0]))
            self.cond_var.set(details.get("condition", CONDITIONS[0]))
            self.avail_var.set(details.get("avail", AVAILABILITY[0]))

            self.desc_ent.delete("1.0", 'end')
            self.desc_ent.insert("1.0", details.get("desc", ""))

            self.tags_ent.delete(0, 'end')
            self.tags_ent.insert(0, details.get("tags", ""))

            self.loc_strategy.set(details.get("loc_strat", "manual"))

            self.loc_ent.delete(0, 'end')
            self.loc_ent.insert(0, details.get("loc", ""))

            self.multi_listing_loc_file_path = details.get("loc_f", "")
            if self.multi_listing_loc_file_path:
                self.lbl_loc_file_status.config(text=f"List Loaded: {os.path.basename(self.multi_listing_loc_file_path)}")

            self.meet_pub.set(details.get("meet_p", False))
            self.meet_door.set(details.get("door_p", False))

            self.img_paths_list = details.get("imgs", [])
            self.refresh_image_panel()

    def commit_bulk_listing_task(self, profiles):
        strat = self.loc_strategy.get()
        details = {
            "title": self.title_ent.get(), "price": self.price_ent.get(), "category": self.cat_var.get(),
            "condition": self.cond_var.get(), "availability": self.avail_var.get(), "desc": self.desc_ent.get("1.0", "end-1c"),
            "tags": self.tags_ent.get(), "public_meetup": self.meet_pub.get(), "door_pickup": self.meet_door.get(), "images": self.img_paths_list
        }

        if not details["title"] or not details["images"]:
            show_alert(self.form, "Deployment Error", "Listing requires Title and Visual Assets (Images). Provide them.", "error")
            return

        if strat == "manual":
            details["location"] = self.loc_ent.get()
        else:
            if not hasattr(self, 'multi_listing_loc_file_path') or not self.multi_listing_loc_file_path:
                show_alert(self.form, "Strategy Error", "List strategy selected but no text file provided. Switch to manual or provide file.", "error")
                return
            details["loc_type"] = "file"
            details["loc_file"] = self.multi_listing_loc_file_path
            details["loc_random"] = True

        self.form.destroy()
        self.add_automated_to_queue(profiles, "listing", details)

if __name__ == "__main__":
    app = ControlPanel()
    app.root.mainloop()