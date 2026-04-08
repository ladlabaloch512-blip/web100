import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from src.automation.selenium_utils import wait_for_page_load, wait_and_find, human_type

def send_discord_alert(webhook_url, profile_name, target_name, messages):
    if not webhook_url or webhook_url == "YOUR_DISCORD_WEBHOOK_HERE":
        return
    content = f"**[New Message Alert]**\n**Profile:** {profile_name}\n**From:** {target_name}\n\n"
    for msg in messages:
        content += f"> {msg}\n"
    data = {"content": content}
    try:
        requests.post(webhook_url, json=data)
    except:
        pass

def monitor_messenger(driver, p_name, state):
    try:
        print(f"[{p_name}] Analyzing Inbox (Waiting for E2EE sync)...")
        driver.get("https://web.facebook.com/messages/")
        wait_for_page_load(driver, state)
        time.sleep(6)

        # Switch to Marketplace Folder
        try:
            print(f"[{p_name}] Switching to Marketplace folder...")
            market_folder_xpath = "//span[text()='Marketplace' and not(ancestor::div[@role='banner'])] | //div[@role='row']//span[text()='Marketplace']"
            market_folder = wait_and_find(driver, market_folder_xpath, state, timeout=5)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", market_folder)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", market_folder)
            time.sleep(4)
        except:
            print(f"[{p_name}] Could not auto-click Marketplace folder, checking current view...")

        print(f"[{p_name}] Ignoring 'Unread' filter button. Scanning for Blue Dot (Unread indicator) instead...")

        # === THE NO-RELOAD DYNAMIC LOOP (Prevents Filter Reset) ===
        processed_hrefs = set()
        collected_chats = []

        # We process up to 10 unread chats per session
        while len(processed_hrefs) < 10:
            if state.GLOBAL_STOP: break

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

                    recent_msgs = chat_history[-5:] if chat_history else []
                    if recent_msgs:
                        print("💬 Last Messages in Chat:")
                        for msg in recent_msgs:
                            print(f"   -> {msg}")
                    else:
                        print("💬 [No text messages found. Client might have used a button or sent an image.]")
                except Exception as history_error:
                    print(f"⚠️ [Could not load chat history: {history_error}]")
                    recent_msgs = []

                # We save this chat offline instead of blocking
                chat_data = {
                    "profile": p_name,
                    "target": target_name,
                    "url": target_href,
                    "messages": recent_msgs,
                }
                collected_chats.append(chat_data)
                send_discord_alert(state.DISCORD_WEBHOOK, p_name, target_name, recent_msgs)

            except Exception as inner_e:
                print(f"⚠️ [{p_name}] Skipped chat due to error: {inner_e}")
                continue

        # At the end of scraping this profile, push to the global state PENDING_MESSAGES
        if collected_chats:
            if not hasattr(state, "PENDING_MESSAGES"):
                state.PENDING_MESSAGES = []

            # Avoid adding duplicates
            existing_urls = [msg["url"] for msg in state.PENDING_MESSAGES]
            for chat in collected_chats:
                if chat["url"] not in existing_urls:
                    state.PENDING_MESSAGES.append(chat)

            state.NEW_MESSAGES_EVENT = True
            print(f"✅ [{p_name}] Saved {len(collected_chats)} unread chats for offline drafting.")
        else:
            print(f"✅ [{p_name}] No unread chats found.")

    except Exception as e:
        print(f"❌ [{p_name}] Inbox monitoring failed: {e}")

def send_messenger_reply(driver, p_name, state, details):
    """
    Called by the worker to send a reply to a specific chat and close.
    details should have: 'url' and 'reply_text'
    """
    try:
        url = details.get("url")
        reply_text = details.get("reply_text")

        if not url or not reply_text:
            return

        print(f"[{p_name}] Opening chat to send reply...")
        driver.get(url)
        wait_for_page_load(driver, state)
        time.sleep(5)

        if state.GLOBAL_STOP:
            return

        msg_box = wait_and_find(driver, "//div[@role='textbox']", state, timeout=10)
        human_type(msg_box, reply_text, fast=True, state_module=state)
        time.sleep(0.5)
        msg_box.send_keys(Keys.ENTER)
        print(f"✅ [{p_name}] Message delivered!")
        time.sleep(4) # Wait for message to be sent
    except Exception as e:
        print(f"❌ [{p_name}] Failed to send reply: {e}")
