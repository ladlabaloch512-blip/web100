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

import src.db_manager.database as db

def perform_listing(driver, details, p_name, state):
    print(f"🛒 [{p_name}] Starting API listing process...")
    try:
        # 1. Go directly to the Marketplace creation page
        driver.get("https://www.facebook.com/marketplace/create/item")
        wait_for_page_load(driver, state)
        time.sleep(5) # Wait for DOM and cookies to load

        # 2. Extract active session data (Session Hijacking)
        print(f"🕵️ [{p_name}] Extracting Security Tokens & Routing Data...")
        cookies, fb_dtsg, jazoest, lsd, profile_id, fb_env = _get_session_data(driver)

        if not fb_dtsg or not profile_id:
            print(f"❌ [{p_name}] Failed to extract security tokens. Is account logged in?")
            return False

        session = requests.Session()
        session.cookies.update(cookies)
        # 🔥 NEW: Added Anti-Bot Headers (x-fb-lsd, x-asbd-id) and fixed Sec-Fetch-Site
        session.headers.update({
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Referer": "https://www.facebook.com/marketplace/create/item",
            "Origin": "https://www.facebook.com",
            "Sec-Fetch-Site": "same-origin",
            "X-FB-LSD": lsd,
            "X-ASBD-ID": "359341"
        })

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

        for i in range(drafts_multiplier):
            if state.GLOBAL_STOP:
                return False

            print(f"\n--- [{p_name}] Processing Draft {i+1} of {drafts_multiplier} ---")

            # Random delay as requested (3-5 seconds)
            delay = random.uniform(3, 5)
            print(f"⏳ [{p_name}] Applying random delay of {delay:.2f} seconds...")
            time.sleep(delay)

            # Pick a random title
            current_title = random.choice(titles_list)

            # Shuffle images
            current_images = original_images.copy()
            random.shuffle(current_images)

            # 3. Upload Images via API
            photo_ids = []
            for img_path in current_images:
                if state.GLOBAL_STOP:
                    return False
                print(f"📸 [{p_name}] Uploading image via API: {img_path}")
                fbid = _api_upload_image(session, img_path, fb_dtsg, jazoest, lsd, profile_id)
                if fbid:
                    photo_ids.append(fbid)
                time.sleep(1)

            if not photo_ids:
                print(f"⚠️ [{p_name}] No images were uploaded successfully for draft {i+1}. Skipping.")
                continue

            if state.GLOBAL_STOP:
                return False

            # Update the details copy with the current title
            current_details = details.copy()
            current_details["title"] = current_title

            # 4. Save Listing as Draft via JS Fetch Injection
            print(f"🚀 [{p_name}] Saving listing '{current_title}' as Draft via Browser XHR Injection...")
            res_json = _api_publish_listing(driver, current_details, photo_ids, fb_dtsg, jazoest, lsd, profile_id)

            if "errors" in res_json:
                print(f"❌ [{p_name}] GraphQL Rejected the Request! FB says:")
                print(json.dumps(res_json["errors"], indent=2))
            elif "data" in res_json:
                try:
                    # Extract the newly created listing ID
                    listing_id = res_json["data"]["marketplace_listing_create"]["marketplace_listing_fbid"]
                    url = f"https://www.facebook.com/marketplace/item/{listing_id}/"
                    print(f"✅ [{p_name}] Draft saved! ID: {listing_id}")
                    db.insert_draft(p_name, listing_id, url, current_title, "Drafted")
                except Exception as ex:
                    print(f"✅ [{p_name}] Draft saved, but could not parse Listing ID. Raw data: {res_json}")
            else:
                print(f"⚠️ [{p_name}] Unknown response format.")
                print(res_json)

        return True
    except Exception as e:
        print(f"⚠️ [{p_name}] Error during API listing: {e}")
        return False
import re
import json
import time
import random
import urllib.parse
import requests

def _get_session_data(driver):
    """Extracts cookies, security tokens, and internal SiteData directly from the browser."""
    cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
    html = driver.page_source

    # Extract fb_dtsg
    dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', html)
    if not dtsg_match:
         dtsg_match = re.search(r'"DTSGInitialData",\[\],\{"token":"(.*?)"', html)
    fb_dtsg = dtsg_match.group(1) if dtsg_match else None

    # Extract LSD
    lsd_match = re.search(r'"LSD",\[\],\{"token":"(.*?)"\}', html)
    if not lsd_match:
        lsd_match = re.search(r'name="lsd" value="(.*?)"', html)
    lsd = lsd_match.group(1) if lsd_match else ""

    # Calculate jazoest
    jazoest = '2' + str(sum(ord(c) for c in fb_dtsg)) if fb_dtsg else ""

    # Extract Profile ID
    user_match = re.search(r'"USER_ID":"(\d+)"', html)
    profile_id = user_match.group(1) if user_match else None

    # Extract hidden GraphQL routing data via Javascript
    fb_env = driver.execute_script("""
        try {
            const sd = require('SiteData');
            return {
                rev: sd.revision || '',
                hsi: sd.hsi || '',
                spin_r: sd.__spin_r || '',
                spin_b: sd.__spin_b || '',
                spin_t: sd.__spin_t || ''
            };
        } catch(e) {
            return {};
        }
    """)

    return cookies, fb_dtsg, jazoest, lsd, profile_id, fb_env

def _api_upload_image(session, image_path, fb_dtsg, jazoest, lsd, profile_id):
    """Uploads a single image directly via API and returns its photo_id."""
    url = f"https://upload.facebook.com/ajax/react_composer/attachments/photo/upload?av={profile_id}&__user={profile_id}&__a=1&fb_dtsg={fb_dtsg}&jazoest={jazoest}&lsd={lsd}"

    data = {
        "fb_dtsg": fb_dtsg,
        "qn": "comet_marketplace_composer",
        "target_id": "355209128917923",
        "source": "8",
        "profile_id": profile_id,
        "waterfallxapp": "comet",
        "upload_id": "1024" # Standard FB behavior
    }

    with open(image_path, 'rb') as f:
        # Force image/jpeg MIME type
        files = {'farr': (image_path.split('/')[-1].split('\\')[-1], f, 'image/jpeg')}
        response = session.post(url, data=data, files=files)

    try:
        raw_text = response.text.replace('for (;;);', '').strip()
        clean_res = json.loads(raw_text)
        payload = clean_res.get('payload')

        if payload and isinstance(payload, dict):
            # FB might return 'fbid' or 'photoID'
            photo_id = payload.get('fbid') or payload.get('photoID')
            if photo_id:
                return str(photo_id)

        print(f"❌ FB rejected the image. Raw Response: {raw_text}")
        return None

    except Exception as e:
        print(f"❌ Failed to parse FB response: {e}")
        return None

def _api_publish_listing(driver, template_data, photo_ids, fb_dtsg, jazoest, lsd, profile_id):
    """Injects a native JS fetch request into the browser with full Form Data sync."""

    CATEGORY_MAP = {
        "Tools": "1670493229902393",
        "Furniture": "1583634935226685",
        "Household": "1569171756675761",
        "Garden": "800089866739547",
        "Appliances": "678754142233400",
        "Video Games": "686977074745292",
        "Books, Movies & Music": "613858625416355",
        "Bags & Luggage": "1567543000236608",
        "Women's clothing & shoes": "1266429133383966",
        "Men's clothing & shoes": "931157863635831",
        "Jewelry & Accessories": "214968118845643",
        "Health & beauty": "1555452698044988",
        "Pet Supplies": "1550246318620997",
        "Baby & kids": "624859874282116",
        "Toys & Games": "606456512821491",
        "Electronics & computers": "1792291877663080",
        "Mobile phones": "1557869527812749",
        "Bicycles": "1658310421102081",
        "Arts & Crafts": "1534799543476160",
        "Sports & Outdoors": "1383948661922113",
        "Auto parts": "757715671026531",
        "Musical Instruments": "676772489112490",
        "Antiques & Collectibles": "393860164117441",
        "Garage Sale": "1834536343472201",
        "Miscellaneous": "895487550471874"
    }

    condition_map = {
        "New": "new", "Used - Like New": "used_like_new",
        "Used - Good": "used_good", "Used - Fair": "used_fair"
    }
    condition_val = condition_map.get(template_data.get('condition'), "used_good")
    cat_id = CATEGORY_MAP.get(template_data.get('category'), "1569171756675761")

    delivery_types = ["IN_PERSON"]
    if template_data.get('door_meetup'):
        delivery_types.append("DOOR_DROPOFF")

    photo_ids = [str(pid) for pid in photo_ids]

    variables = {
        "input": {
            "actor_id": str(profile_id),
            "client_mutation_id": str(random.randint(1, 20)),
            # Updated to match FB's new strict multi-component tracking format
            "attribution_id_v2": f"CometMarketplaceComposerRoot.react,comet.marketplace.composer,unexpected,{int(time.time()*1000)},202263,1606854132932955,,;CometMarketplaceComposerCreateComponent.react,comet.marketplace.composer.create,unexpected,{int(time.time()*1000)},144350,1606854132932955,,;",
            "audience": {"marketplace": {"marketplace_id": "1663689853903557"}},
            "data": {
                "common": {
                    "attribute_data_json": json.dumps({"condition": condition_val}, separators=(',', ':')),
                    "category_id": str(cat_id),
                    "commerce_shipping_carrier": None,
                    "commerce_shipping_carriers": [],
                    "comparable_price": "null",
                    "cost_per_additional_item": None,
                    "delivery_types": delivery_types,
                    "description": {"text": str(template_data.get('desc') or '')},
                    "draft_type": "COMMERCE_SELL_OPTIONS",
                    "hidden_from_friends_visibility": "VISIBLE_TO_EVERYONE",
                    "is_personalization_required": None,
                    "is_photo_order_set_by_seller": False,
                    "is_preview": False,
                    "item_price": {"currency": "USD", "price": str(template_data.get('price') or '0')},
                    "latitude": 31.5204,
                    "listing_email_id": None,
                    "longitude": 74.3587,
                    "min_acceptable_checkout_offer_price": "null",
                    "personalization_info": None,
                    "product_hashtag_names": [],
                    "quantity": -1 if template_data.get('availability') == "List as Single Item" else 1,
                    "shipping_calculation_logic_version": None,
                    "shipping_cost_option": "BUYER_PAID_SHIPPING",
                    "shipping_cost_range_lower_cost": None,
                    "shipping_cost_range_upper_cost": None,
                    "shipping_label_price": "0",
                    "shipping_label_rate_code": None,
                    "shipping_label_rate_type": None,
                    "shipping_offered": False,
                    "shipping_options_data": [],
                    "shipping_package_weight": None,
                    "shipping_price": "null",
                    "shipping_service_type": None,
                    "sku": "",
                    "source_type": "marketplace_unknown",
                    "suggested_hashtag_names": [],
                    "surface": "composer",
                    "title": str(template_data.get('title') or 'Listing'),
                    "video_ids": [],
                    "xpost_target_ids": [],
                    "comments_disabled": True,
                    "photo_ids": photo_ids
                }
            }
        }
    }

    # Force exact form-data structure Facebook expects
    data = {
        "av": profile_id,
        "__user": profile_id,
        "__a": "1",
        "__req": "2a",
        "__aaid": "0",
        "fb_dtsg": fb_dtsg,
        "jazoest": jazoest,
        "lsd": lsd,
        "__comet_req": "15", # Added: Required for modern FB routing
        "__crn": "comet.fbweb.CometMarketplaceComposerRoute",
        "qpl_active_flow_ids": "138820675",
        "fb_api_caller_class": "RelayModern",
        "fb_api_req_friendly_name": "useCometMarketplaceListingCreateMutation",
        "variables": json.dumps(variables, separators=(',', ':')),
        "server_timestamps": "true",
        "fb_api_analytics_tags": '["qpl_active_flow_ids=138820675"]',
        "doc_id": "9551550371629242"
    }

    encoded_data = urllib.parse.urlencode(data)
    driver.set_script_timeout(15)

    # SMARTER JS: Uses string concatenation to avoid data corruption and passes LSD explicitly
    js_code = """
    var done = arguments[arguments.length - 1];
    var base_payload = arguments[0];
    var passed_lsd = arguments[1];

    var sd = {};
    try { sd = require('SiteData'); } catch(e) {}

    // Append SiteData safely without using URLSearchParams which corrupts JSON strings
    var body_str = base_payload;
    if(sd.revision) body_str += '&__rev=' + sd.revision;
    if(sd.hsi) body_str += '&__hsi=' + sd.hsi;
    if(sd.__spin_r) body_str += '&__spin_r=' + sd.__spin_r;
    if(sd.__spin_b) body_str += '&__spin_b=' + sd.__spin_b;
    if(sd.__spin_t) body_str += '&__spin_t=' + sd.__spin_t;

    fetch("https://www.facebook.com/api/graphql/", {
        method: "POST",
        credentials: "same-origin", // CRITICAL: Ensures session cookies are sent
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-FB-Friendly-Name": "useCometMarketplaceListingCreateMutation",
            "X-FB-LSD": passed_lsd,
            "X-ASBD-ID": "359341"
        },
        body: body_str
    })
    .then(response => response.text())
    .then(text => {
        var cleanText = text.replace('for (;;);', '').trim();
        return JSON.parse(cleanText);
    })
    .then(data => done(data))
    .catch(error => done({"errors": [{"message": "JS Fetch failed: " + error}]}));
    """

    # Pass LSD explicitly as the second argument
    response_json = driver.execute_async_script(js_code, encoded_data, lsd)
    return response_json
