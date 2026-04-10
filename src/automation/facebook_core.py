import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.automation.selenium_utils import human_type, wait_for_page_load, wait_and_find, wait_and_click, js_click

def perform_manual(driver, p_name, target_url, state):
    try:
        driver.get(target_url)
        print(f"[{p_name}] Browser opened manually.")
        while len(driver.window_handles) > 0:
            if state.GLOBAL_STOP:
                break
            time.sleep(2)
    except:
        pass

def perform_login(driver, email, password, p_name, state):
    driver.get("https://web.facebook.com")
    wait_for_page_load(driver, state)
    time.sleep(3)
    if state.GLOBAL_STOP:
        return False

    try:
        email_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "email")))
        print(f"[{p_name}] Logging in...")
        human_type(email_field, email, False, state)
        pass_field = driver.find_element(By.NAME, "pass")
        human_type(pass_field, password, False, state)
        if state.GLOBAL_STOP:
            return False
        pass_field.send_keys(Keys.ENTER)
        time.sleep(7)

        max_wait_time = 300
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            if state.GLOBAL_STOP:
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

import time
import random
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.automation.selenium_utils import human_type, wait_for_page_load, wait_and_find, wait_and_click, js_click
import src.db_manager.database as db

def perform_listing(driver, details, p_name, state):
    print(f"🛒 [{p_name}] Starting UI-based listing process...")

    titles_list = []
    if details.get("title_type") == "file":
        try:
            with open(details["title_file"], "r") as f:
                titles_list = [t.strip() for t in f.readlines() if t.strip()]
        except Exception:
            titles_list = [details.get("title", "Listing")]
    else:
        titles_list = [details.get("title", "Listing")]

    drafts_multiplier = details.get("drafts_multiplier", 1)
    original_images = details.get('images', [])
    direct_publish = details.get('direct_publish', False)

    for i in range(drafts_multiplier):
        if state.GLOBAL_STOP:
            return False

        print(f"\n--- [{p_name}] Processing Item {i+1} of {drafts_multiplier} ---")

        current_title = random.choice(titles_list)
        current_images = original_images.copy()
        random.shuffle(current_images)

        try:
            print(f"[{p_name}] Constructing Marketplace Listing UI...")
            driver.get("https://web.facebook.com/marketplace/create/item")
            wait_for_page_load(driver, state)
            time.sleep(4)

            wait_and_find(driver, "//input[@type='file']", state).send_keys("\n".join(current_images))
            time.sleep(5)

            try:
                # Highly robust Javascript fallback for Title
                title_box = wait_and_find(driver, "//label[@aria-label='Title']//input | //span[text()='Title']/ancestor::label//input | //span[contains(text(), 'Title')]/following::input[1]", state, timeout=15)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", title_box)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", title_box)
                human_type(title_box, current_title, False, state)
            except Exception as e:
                print(f"[{p_name}] ⚠️ Fallback injecting Title... ({e})")
                driver.execute_script("""
                var el = document.evaluate("//label[@aria-label='Title']//input | //span[text()='Title']/ancestor::label//input | //span[contains(text(), 'Title')]/following::input[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if(el) { el.value = arguments[0]; el.dispatchEvent(new Event('input', { bubbles: true })); }
                """, current_title)

            try:
                # Highly robust Javascript fallback for Price
                price_box = wait_and_find(driver, "//label[@aria-label='Price']//input | //span[text()='Price']/ancestor::label//input | //span[contains(text(), 'Price')]/following::input[1]", state, timeout=15)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", price_box)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", price_box)
                human_type(price_box, details['price'], False, state)
            except Exception as e:
                print(f"[{p_name}] ⚠️ Fallback injecting Price... ({e})")
                driver.execute_script("""
                var el = document.evaluate("//label[@aria-label='Price']//input | //span[text()='Price']/ancestor::label//input | //span[contains(text(), 'Price')]/following::input[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if(el) { el.value = arguments[0]; el.dispatchEvent(new Event('input', { bubbles: true })); }
                """, details['price'])

            try:
                wait_and_click(driver, "//label[@aria-label='Category'] | //span[text()='Category']/ancestor::label | //span[contains(text(), 'Category')]/following::div[1]", state, timeout=10)
                time.sleep(1.5)
                js_click(driver, f'//span[text()="{details["category"]}"]', state)
                time.sleep(1)
            except Exception as e:
                print(f"[{p_name}] ⚠️ Fallback Category dropdown: {e}")

            try:
                # Pure Javascript automation to aggressively crawl the DOM layout for the Condition combobox
                js_open_condition = """
                var spans = document.querySelectorAll('span');
                for (var i = 0; i < spans.length; i++) {
                    if (spans[i].innerText && spans[i].innerText.trim().toLowerCase() === 'condition') {
                        var node = spans[i];
                        // Walk up looking for a label, or up to 4 parents if no label
                        var wrapper = node.closest('label');
                        if (!wrapper) {
                            wrapper = node.parentElement;
                            for (var j = 0; j < 3; j++) { if(wrapper.parentElement) wrapper = wrapper.parentElement; }
                        }

                        var combobox = wrapper.querySelector('div[role="combobox"]') ||
                                       wrapper.querySelector('div[tabindex="0"]') ||
                                       wrapper.querySelector('div[role="button"]');
                        if (combobox) {
                            combobox.scrollIntoView({block: 'center'});
                            combobox.click();
                            return true;
                        }
                    }
                }
                return false;
                """
                success = driver.execute_script(js_open_condition)
                if not success:
                    print(f"[{p_name}] ⚠️ JS combobox finder failed, falling back to XPath...")
                    # Fallback XPath 1: Click directly using the aria-label label mapping
                    condition_label_xpath = "//label[contains(@aria-label, 'Condition')] | //span[text()='Condition' or text()='condition']/ancestor::label"
                    condition_btn = wait_and_find(driver, condition_label_xpath, state, timeout=10)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", condition_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", condition_btn)
                time.sleep(1.5)

                # The dropdown menu opens at the end of the body in a portal
                target_condition = details["condition"]
                js_select_condition = f"""
                var options = document.querySelectorAll('div[role="option"] span');
                for (var i = 0; i < options.length; i++) {{
                    if (options[i].innerText === '{target_condition}') {{
                        options[i].click();
                        return true;
                    }}
                }}
                return false;
                """
                success = driver.execute_script(js_select_condition)
                if not success:
                    print(f"[{p_name}] ⚠️ JS option selector failed for '{target_condition}', trying XPath...")
                    condition_option_xpath = f"//div[@role='option']//span[text()='{target_condition}'] | //span[text()='{target_condition}']"
                    condition_opt = wait_and_find(driver, condition_option_xpath, state, timeout=5)
                    driver.execute_script("arguments[0].click();", condition_opt)

                time.sleep(1)
            except Exception as e:
                print(f"[{p_name}] ⚠️ Failed to set Condition dropdown: {e}")

            try:
                # Highly robust Javascript search for 'More details' or 'more details' ignoring case and nesting
                js_more_btn = """
                var spans = document.querySelectorAll('span');
                for (var i = 0; i < spans.length; i++) {
                    if (spans[i].innerText && spans[i].innerText.toLowerCase().includes('more details')) {
                        return spans[i];
                    }
                }
                return null;
                """
                more_btn = driver.execute_script(js_more_btn)
                if more_btn:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", more_btn)
                    time.sleep(2)
            except Exception as e:
                print(f"[{p_name}] ⚠️ More details click failed/not found: {e}")

            try:
                desc_box = wait_and_find(driver, "//label[@aria-label='Description']//textarea | //span[contains(text(), 'Description')]/following::textarea[1]", state, timeout=5)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", desc_box)
                human_type(desc_box, details['desc'], fast=True, state_module=state)
                time.sleep(1)
            except Exception as e:
                print(f"[{p_name}] Description field skipped: {e}")

            if details.get('availability') and details['availability'] != "List as Single Item":
                try:
                    avail_box = wait_and_find(driver, "//label[@aria-label='Availability'] | //span[contains(text(), 'Availability')]/following::div[1]", state, timeout=5)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", avail_box)
                    time.sleep(1)
                    avail_box.click()
                    time.sleep(1)
                    js_click(driver, f'//span[text()="{details["availability"]}"]', state)
                except:
                    pass

            if details.get('tags'):
                try:
                    tag_box = wait_and_find(driver, "//label[@aria-label='Product tags']//textarea | //span[contains(text(), 'Product tags')]/following::textarea[1]", state, timeout=5)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tag_box)
                    human_type(tag_box, details['tags'], fast=True, state_module=state)
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
                    loc_box = wait_and_find(driver, "//label[@aria-label='Location']//input", state, timeout=5)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", loc_box)
                    loc_box.send_keys(Keys.CONTROL + "a")
                    loc_box.send_keys(Keys.BACKSPACE)
                    human_type(loc_box, location_to_type, False, state)
                    time.sleep(3)
                    loc_box.send_keys(Keys.ARROW_DOWN)
                    loc_box.send_keys(Keys.ENTER)
                except:
                    pass

            if details.get('public_meetup'):
                try: js_click(driver, "//span[text()='Public meetup']", state, timeout=3)
                except: pass
            if details.get('door_pickup'):
                try: js_click(driver, "//span[text()='Door pickup']", state, timeout=3)
                except: pass

            time.sleep(2)
            if not state.GLOBAL_STOP:
                print(f"[{p_name}] Proceeding...")

                try:
                    next_btn_xpath = "//div[@aria-label='Next'] | //span[text()='Next'] | //div[@role='button']//span[text()='Next']"
                    next_btn = wait_and_find(driver, next_btn_xpath, state, timeout=10)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(4)
                except Exception as e:
                    print(f"[{p_name}] Next button issue: {e}")

                try:
                    if direct_publish:
                        action_btn_xpath = "//div[@aria-label='Publish'] | //span[text()='Publish'] | //div[@role='button']//span[contains(text(), 'Publish')]"
                    else:
                        action_btn_xpath = "//div[@aria-label='Save draft'] | //span[text()='Save draft'] | //div[@role='button']//span[contains(text(), 'Save draft')]"

                    action_btn = wait_and_find(driver, action_btn_xpath, state, timeout=10)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", action_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", action_btn)

                    if direct_publish:
                        print(f"✅ [{p_name}] Listing POSTED and PUBLISHED successfully!")
                        state.update_status(p_name, "✅ Published")
                        time.sleep(10)
                    else:
                        print(f"✅ [{p_name}] Listing saved as Draft successfully!")
                        state.update_status(p_name, "✅ Drafted")
                        time.sleep(10) # wait for redirect back to marketplace home or listing page

                        # Capture Draft URL
                        current_url = driver.current_url
                        listing_id = current_url.rstrip('/').split('/')[-1] if 'item' in current_url else f"DRAFT_{int(time.time())}"

                        if 'item' not in current_url:
                            # Fallback if redirect doesn't land on the item page directly
                            driver.get("https://web.facebook.com/marketplace/you/selling")
                            time.sleep(5)
                            try:
                                first_item = driver.find_element(By.XPATH, "(//a[contains(@href, '/marketplace/item/')])[1]")
                                current_url = first_item.get_attribute('href')
                                listing_id = current_url.rstrip('/').split('/')[-1]
                            except:
                                print(f"⚠️ [{p_name}] Could not extract direct URL. Saving dummy URL.")
                                current_url = f"https://web.facebook.com/marketplace/you/selling"

                        db.insert_draft(p_name, listing_id, current_url, current_title, "Drafted")
                        print(f"✅ [{p_name}] Draft URL saved to DB: {current_url}")

                except Exception as e:
                    print(f"❌ [{p_name}] Failed to complete listing action: {e}")
                    state.update_status(p_name, "❌ Listing Failed")
                    time.sleep(15)

        except Exception as e:
            if not state.GLOBAL_STOP:
                print(f"❌ [{p_name}] Error during UI listing: {e}")
                state.update_status(p_name, "❌ Script Error")
                time.sleep(15)

    return True
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.automation.selenium_utils import wait_for_page_load
import src.state as state

def perform_human_activity(driver, p_name, state_module):
    print(f"🚶‍♂️ [{p_name}] Starting Human Activity (Warm-up) process...")
    try:
        driver.get("https://web.facebook.com")
        wait_for_page_load(driver, state_module)
        time.sleep(random.uniform(5, 8))

        # Check if we are on the login page or checkpoint
        current_url = driver.current_url.lower()
        if "login" in current_url or "checkpoint" in current_url:
            print(f"⚠️ [{p_name}] Cannot perform human activity: Account is not logged in or is on checkpoint.")
            return False

        print(f"[{p_name}] Browsing feed...")
        scroll_count = random.randint(10, 25)
        likes_done = 0
        target_likes = random.randint(1, 4)

        for i in range(scroll_count):
            if state_module.GLOBAL_STOP:
                return False

            # Scroll down randomly
            scroll_amt = random.randint(300, 900)
            driver.execute_script(f"window.scrollBy(0, {scroll_amt});")

            # Pause to "read"
            time.sleep(random.uniform(1.5, 4.5))

            # Occasional Like
            if likes_done < target_likes and random.random() < 0.15:
                try:
                    like_btns = driver.find_elements(By.XPATH, "//div[@aria-label='Like' and @role='button']")
                    if like_btns:
                        target = random.choice(like_btns)
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
                        time.sleep(random.uniform(0.5, 1.5))
                        driver.execute_script("arguments[0].click();", target)
                        likes_done += 1
                        print(f"👍 [{p_name}] Liked a post! ({likes_done}/{target_likes})")
                        time.sleep(random.uniform(1.0, 3.0))
                except Exception as e:
                    pass

        print(f"✅ [{p_name}] Human Activity complete. Scrolled {scroll_count} times, liked {likes_done} posts.")
        return True

    except Exception as e:
        print(f"❌ [{p_name}] Error during Human Activity: {e}")
        return False
