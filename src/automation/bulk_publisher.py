import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.automation.selenium_utils import wait_for_page_load
import src.state.database as db
import src.state as state

def publish_drafts(driver, p_name, tabs_count):
    print(f"🚀 [{p_name}] Starting bulk publisher from drafts...")
    drafts = db.get_drafts_by_profile(p_name, status="Drafted")

    if not drafts:
        print(f"✅ [{p_name}] No pending drafts found in database.")
        return

    print(f"[{p_name}] Found {len(drafts)} drafts to publish.")

    current_tab = 0
    # Process drafts in batches matching the tabs_count
    for i in range(0, len(drafts), tabs_count):
        if state.GLOBAL_STOP:
            break

        batch = drafts[i:i + tabs_count]

        # Open tabs for the batch
        for j, draft in enumerate(batch):
            listing_id, url, title = draft
            print(f"[{p_name}] Opening Draft: {title}")

            if j == 0 and len(driver.window_handles) == 1:
                driver.get(url)
            else:
                driver.execute_script(f"window.open('{url}', '_blank');")
                driver.switch_to.window(driver.window_handles[-1])

            time.sleep(2)

        # Iterate through tabs and publish
        for handle in driver.window_handles:
            if state.GLOBAL_STOP:
                break

            driver.switch_to.window(handle)
            wait_for_page_load(driver, state)

            # Allow time for JS to render the publish button
            time.sleep(3)

            try:
                # The "Publish" button on a drafted listing page.
                publish_btn_xpath = "//div[@aria-label='Publish' and @role='button'] | //span[text()='Publish']/ancestor::div[@role='button']"
                publish_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, publish_btn_xpath)))

                # Use JS click to avoid 'element not interactable' issues
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", publish_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", publish_btn)

                print(f"✅ [{p_name}] Clicked Publish!")

                # Try to extract the listing ID from the URL to update DB
                current_url = driver.current_url
                for draft in batch:
                    if draft[1] in current_url or draft[0] in current_url:
                        db.update_draft_status(draft[0], "Published")
                        break

                time.sleep(random.uniform(4, 7)) # Delay between publishes

            except Exception as e:
                print(f"⚠️ [{p_name}] Could not find Publish button for this draft: {e}")

        # Close extra tabs after processing batch, leave one open
        while len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            driver.close()

        driver.switch_to.window(driver.window_handles[0])
