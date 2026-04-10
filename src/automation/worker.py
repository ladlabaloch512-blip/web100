import time
import src.state as state
from src.utils.system_utils import check_login_status, force_kill_browser, smart_cleanup
from src.browser.launcher import launch_browser
from src.automation.facebook_core import perform_login, perform_listing, perform_manual, perform_human_activity
from src.automation.messenger import monitor_messenger, send_messenger_reply
from src.automation.bulk_publisher import publish_drafts

def worker_task(p_name, task_type, details=None, email=None, pwd=None, progress_callback=None):
    if state.GLOBAL_STOP:
        return
    print(f"\n🚀 Engaging profile: {p_name}")
    driver = None
    try:
        driver = launch_browser(p_name, state.BASE_PATH, state)
        if task_type == "login":
            perform_login(driver, email, pwd, p_name, state)
        elif task_type == "listing":
            perform_listing(driver, details, p_name, state)
        elif task_type == "publish_drafts":
            tabs_count = details.get("tabs_count", 3)
            publish_drafts(driver, p_name, tabs_count)
        elif task_type == "messenger":
            monitor_messenger(driver, p_name, state)
        elif task_type == "messenger_reply":
            send_messenger_reply(driver, p_name, state, details)
        elif task_type == "human_activity":
            duration = details.get("duration_minutes", 1) if details else 1
            res = perform_human_activity(driver, p_name, state, duration)
            if res:
                state.update_status(p_name, "✅ Warmed Up")
        elif task_type == "health_check":
            from selenium.webdriver.common.by import By
            from src.automation.selenium_utils import wait_for_page_load

            driver.get("https://web.facebook.com")
            wait_for_page_load(driver, state)
            time.sleep(5)

            current_url = driver.current_url.lower()
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            except:
                body_text = ""

            if "suspended" in body_text or "disabled" in current_url:
                state.app_config[f"status_{p_name}"] = "🔴 Disabled"
            elif "checkpoint" in current_url or "two_step" in current_url or "challenge" in current_url:
                state.app_config[f"status_{p_name}"] = "🟡 Checkpoint"
            elif "login" in current_url or "incorrect" in body_text:
                state.app_config[f"status_{p_name}"] = "⚪ Logged Out"
            else:
                state.app_config[f"status_{p_name}"] = "🟢 Ready"

            state.save_config(state.app_config)

        elif task_type == "manual":
            perform_manual(driver, p_name, details.get("url", "https://web.facebook.com"), state)
    except Exception as e:
        if not state.GLOBAL_STOP:
            print(f"❌ CRITICAL ERROR on {p_name}: {e}")
            state.update_status(p_name, "❌ Crashed")
    finally:
        if driver:
            if task_type == "login" and check_login_status(p_name, state.BASE_PATH):
                time.sleep(10)
            force_kill_browser(driver, profile_name=p_name)
            if driver in state.ACTIVE_DRIVERS:
                state.ACTIVE_DRIVERS.remove(driver)

        smart_cleanup(p_name, state.BASE_PATH)
        if progress_callback:
            progress_callback()
