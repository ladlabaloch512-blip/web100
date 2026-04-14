# Abiz Global Enterprise Dashboard

**Abiz Global Enterprise Dashboard** is a powerful, multi-profile browser automation tool designed specifically for Facebook Marketplace and Messenger management. It utilizes `undetected_chromedriver` for stealthy operation, allowing you to manage numerous profiles, automate bulk listings, monitor messages, and streamline your entire Facebook workflow from a single, modern Flet-based interface.

---

## 🚀 Key Features

### 1. Multi-Profile Architecture & Management
*   **Persistent Profiles:** Automatically saves browser data (Cookies, Cache, History) to individual profile folders (e.g., `C:\Work\Profiles`). No need to re-login repeatedly.
*   **Bulk Profile Creation:** Instantly provision up to hundreds of new profiles. The tool automatically creates desktop shortcuts via VBS script that launch Chrome directly into that specific profile.
*   **Fingerprint Randomization:** Assigns a unique User-Agent and Screen Resolution to every profile upon creation. This prevents Facebook from linking profiles together and mitigates bot detection.
*   **Bulk Health Checks:** Select multiple profiles and run a health check. The bot opens Facebook and verifies if the account is `🟢 Logged In`, `⚪ Logged Out`, or `🔴 Suspended/Checkpoint`.
*   **Smart Cleanup:** A built-in "Clear Cache & Temp" button allows you to delete heavy `GPUCache`, `Service Worker`, and `Network\Cache` folders for all selected profiles, saving gigabytes of disk space while keeping logins intact.
*   **Profile Deletion:** Securely and completely wipe a profile and its entire data directory from disk in one click.

### 2. Marketplace Automation (The Listing Engine)
*   **Dual Engine Support:**
    *   **Standard UI Engine:** Navigates the Facebook DOM visually, clicking buttons and typing text simulating a real human. Best for high-security accounts.
    *   **Ultra Fast API Engine (GraphQL/XHR):** Injects listings directly into Facebook's backend via session cookies and API requests. Lightning fast for bulk drafting.
*   **Dynamic Data Strategies:**
    *   **Title/Description Randomization:** Load a `.txt` file containing hundreds of titles or descriptions (one per line). The bot will randomly pick one for each listing, ensuring no two listings look exactly identical to Facebook's spam filters.
    *   **Location Strategy:** Manually type a city, or load a `.txt` file of zip codes/cities to randomly distribute your listings across different geographic areas.
*   **Multi-Image Upload & Optimization:** Select multiple images. The bot compresses them using the `Pillow` library to save bandwidth and dynamically renames them before upload to bypass image hash tracking.
*   **Draft Generation (Multipliers):** Want to post the same item 5 times on one profile? Set the "Drafts Multiplier" to 5. The bot will create 5 identical drafts and save their unique IDs to an SQLite database.
*   **Bulk Publisher:** A dedicated module that connects to the SQLite database and rapidly publishes all pending drafts across your selected profiles.
*   **Template Configs (JSON):** Save your entire listing configuration (Titles, Prices, Categories, loaded TXT files, checkboxes) into a `.json` file and load it back instantly later.

### 3. Messenger Automation (The Chat Bot)
*   **Background Inbox Monitoring:** The tool opens Messenger in the background and scans specifically for the "Unread" blue dot indicator, completely ignoring read messages and system suggestions.
*   **Live Context Reading:** Once an unread chat is found, it extracts the last 5-6 text messages and filters out Facebook junk (like "Active Now" or E2EE notices).
*   **Centralized Messenger Hub:**
    *   Instead of switching between 10 browser windows, all unread chats are routed back to the **Messenger Hub** tab inside the Flet Dashboard.
    *   The sidebar displays which profiles have pending messages.
    *   Click a profile to view the chat bubbles directly in the UI.
    *   Type your reply in the Dashboard, hit Send, and the automation engine routes it back to the specific profile's browser in the background.

### 4. Technical Core & Task Queue
*   **Multi-Threading (ThreadPoolExecutor):** Run tasks across 1 to 10+ profiles simultaneously. You decide the concurrency level.
*   **Persistent Queue System:** Queue up multiple tasks (e.g., Login 5 profiles, then List on 3 profiles, then Check Health on 2). The Master Queue processes them sequentially or in parallel based on your thread count.
*   **Sequential Launcher (Port Clash Fix):** Browsers are launched with a strict 1.5-second delay between each thread. This prevents ChromeDriver debug port collisions and the dreaded "Blank Tab" error.
*   **Emergency Stop (Ghost Process Killer):** A panic button that not only stops the Python threads but uses `psutil` and `wmic` to aggressively hunt down and kill all lingering `chrome.exe` and `chromedriver.exe` child processes linked to the active profiles.
*   **Task Scheduling:** Set a future date and time for the Master Queue to begin executing automatically.

---

## 🛠️ User Guide

### 1. Initial Setup
1. Launch the application (`python main.py`).
2. On the very first run, you will be prompted to select a **Master Directory** (e.g., a folder on your Desktop or `C:\Work\Profiles`). This is where all profile data will be permanently stored.
3. Once loaded, the main dashboard will appear.

### 2. Creating & Managing Profiles
*   Click **Profile Management -> Create Profiles**. Enter the number of profiles you want (e.g., 5) and confirm the path to your system's `chrome.exe`. Flet will provision them and create desktop shortcuts in the folder you selected.
*   **To Check Health:** Check the boxes next to your profiles in the Profile Directory, click **Health Check**, and then click **Run Master Queue** at the top right.
*   **To Save Space:** Check the boxes, click **Clean Cache & Temp**, and confirm.

### 3. Automating a Listing
1. Go to **Automation (Multi) -> Queued Multi-Listing**. This opens the Deployment Configurator.
2. Fill out the **Basic Configuration** (Title, Price, Images). Note: You can use the radio buttons to switch from "Manual Entry" to "Load from TXT File" for titles/descriptions.
3. Fill out the **Taxonomy** (Category, Condition, Search Tags).
4. Fill out **Settings & Deploy** (Location strategy, Fulfillment preferences).
5. Choose your **Execution Mode**: `Standard UI` (slower, safer) or `API Mode` (fast).
6. Click **+ ADD TO MULTI-DEPLOY QUEUE**.
7. Close the configurator window, ensure your target profiles are checked in the main dashboard, and click **Run Master Queue**.

### 4. Handling Messages
1. Select the profiles you want to monitor in the dashboard.
2. Click **Queued Messenger Inbox**.
3. Click **Run Master Queue**.
4. The bots will launch and begin scanning. If a new message is found, you will hear a "Ping" sound.
5. Switch to the **Messenger Hub** tab at the top of the dashboard.
6. Look at the left sidebar to see which profile received the message. Click it.
7. Read the chat history in the main window, type your reply in the input box, and hit the Send icon.

### 5. Managing the Queue & Emergency Stops
*   The system operates on a "Queue -> Run" philosophy. You queue up actions first, then run them.
*   If a task hangs, or you need to stop immediately, click the **🔴 Stop All** button. This will wipe the queue and forcefully kill all associated browser processes.
