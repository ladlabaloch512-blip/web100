import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.automation.selenium_utils import wait_for_page_load
import src.db_manager.database as db
import src.state as state

def publish_drafts(driver, p_name, tabs_count):
    print(f"🚀 [{p_name}] Starting dynamic bulk publisher from drafts...")
    drafts = db.get_drafts_by_profile(p_name, status="Drafted")

    if not drafts:
        print(f"✅ [{p_name}] No pending drafts found in database.")
        return

    print(f"[{p_name}] Found {len(drafts)} drafts to publish.")

    # We will treat `drafts` as a queue
    active_tasks = {} # maps window handle to draft info (listing_id, url, title)

    # Seed the initial tabs
    initial_batch_size = min(tabs_count, len(drafts))

    for i in range(initial_batch_size):
        draft = drafts.pop(0)
        listing_id, url, title = draft
        print(f"[{p_name}] Opening Draft: {title}")

        if i == 0 and len(driver.window_handles) == 1:
            driver.get(url)
            active_tasks[driver.window_handles[0]] = draft
        else:
            driver.execute_script(f"window.open('{url}', '_blank');")
            new_handle = driver.window_handles[-1]
            active_tasks[new_handle] = draft

        time.sleep(2)

    # Process tabs continuously
    while active_tasks and not state.GLOBAL_STOP:
        # We take a snapshot of handles to iterate over
        current_handles = list(active_tasks.keys())

        for handle in current_handles:
            if state.GLOBAL_STOP:
                break

            try:
                driver.switch_to.window(handle)
                draft = active_tasks[handle]
                listing_id, url, title = draft

                # We check if the page is ready and if the publish button exists
                wait_for_page_load(driver, state)

                # Check for Publish button
                publish_btn_xpath = "//div[@aria-label='Publish' and @role='button'] | //span[text()='Publish']/ancestor::div[@role='button']"

                try:
                    publish_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, publish_btn_xpath)))
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", publish_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", publish_btn)
                    print(f"✅ [{p_name}] Clicked Publish for '{title}'!")

                    db.update_draft_status(listing_id, "Published")
                    state.update_status(p_name, "✅ Bulk Published")
                    time.sleep(random.uniform(2, 4))

                    # Close the tab, remove from active tasks
                    if len(driver.window_handles) > 1:
                        driver.close()
                    del active_tasks[handle]

                    # If we have more drafts waiting, open a new tab immediately
                    if drafts and not state.GLOBAL_STOP:
                        next_draft = drafts.pop(0)
                        driver.switch_to.window(driver.window_handles[-1]) # switch to any remaining open tab safely
                        driver.execute_script(f"window.open('{next_draft[1]}', '_blank');")
                        new_handle = driver.window_handles[-1]
                        active_tasks[new_handle] = next_draft
                        print(f"[{p_name}] Replaced finished tab with new Draft: {next_draft[2]}")
                        time.sleep(2)

                except Exception as wait_e:
                    # Publish button not ready yet or page loading, we will check it again next loop
                    pass

            except Exception as e:
                print(f"⚠️ [{p_name}] Error processing tab for draft '{draft[2]}': {e}")
                # We won't close the tab or remove from active tasks immediately on general error,
                # but if it's completely stuck it might hang.
                # Let's add a safe guard
                try:
                    current_url = driver.current_url
                    if "facebook.com" not in current_url:
                        del active_tasks[handle]
                except:
                    pass

        time.sleep(3) # Small delay before looping through handles again to prevent CPU hogging

    # Final cleanup of remaining tabs
    while len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])
        driver.close()

    driver.switch_to.window(driver.window_handles[0])
    print(f"🎉 [{p_name}] Bulk publishing completed!")
