import time
import src.state as state
from src.utils.system_utils import check_login_status, force_kill_browser, smart_cleanup
from src.browser.launcher import launch_browser
from src.automation.facebook_core import perform_login, perform_listing, perform_manual
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
        elif task_type == "manual":
            perform_manual(driver, p_name, details.get("url", "https://web.facebook.com"), state)
    except Exception as e:
        if not state.GLOBAL_STOP:
            print(f"❌ CRITICAL ERROR on {p_name}: {e}")
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
