import time
import random
import requests
import re
import json
import urllib.parse
import undetected_chromedriver as uc
import src.db_manager.database as db

class MarketplaceLister:
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
    def __init__(self):
        pass

    def create_listing(self, driver, profile_dir, template_data, action="draft", current_title=None):
        """Creates listing using Hybrid API approach. Action can be 'draft' or 'publish'."""
        print(f"🛒 [{profile_dir}] Starting API listing process... (Action: {action.upper()})")
        if not current_title:
            current_title = template_data.get('title', 'Listing')

        try:
            # 2. Go directly to the Marketplace creation page
            print(f"🌐 [{profile_dir}] Opening Marketplace creation page. Ensure you are logged in!")
            driver.get("https://web.facebook.com/marketplace/create/item")
            time.sleep(10) # Wait for manual login (if needed) and DOM/cookies to load

            # 3. Extract active session data
            print(f"🕵️ [{profile_dir}] Extracting Security Tokens & Routing Data...")
            cookies, fb_dtsg, jazoest, lsd, profile_id, fb_env = self._get_session_data(driver)
            if not fb_dtsg or not profile_id:
                print(f"❌ [{profile_dir}] Failed to extract security tokens. Is account logged in?")
                return False

            session = requests.Session()
            session.cookies.update(cookies)
            # Add Anti-Bot Headers
            user_agent = driver.execute_script("return navigator.userAgent;")
            session.headers.update({
                "User-Agent": user_agent,
                "Referer": "https://web.facebook.com/marketplace/create/item",
                "Origin": "https://web.facebook.com",
                "Sec-Fetch-Site": "same-origin",
                "X-FB-LSD": lsd,
                "X-ASBD-ID": "359341"
            })

            # 4. Upload Images via API
            photo_ids = []
            for img_path in template_data.get('images', []):
                print(f"📸 [{profile_dir}] Uploading image via API: {img_path}")
                fbid = self._api_upload_image(session, img_path, fb_dtsg, jazoest, lsd, profile_id)
                if fbid:
                    photo_ids.append(fbid)
                time.sleep(1)

            if not photo_ids and template_data.get('images', []):
                print(f"⚠️ [{profile_dir}] No images were uploaded successfully, aborting API listing.")
                return False

            # Override title in template data for this specific run
            template_data['title'] = current_title

            # 5. Execute Action (Draft or Publish)
            if action == "publish":
                res_json = self.publish_listing(driver, template_data, photo_ids, fb_dtsg, jazoest, lsd, profile_id)
            else:
                res_json = self.draft_listing(driver, template_data, photo_ids, fb_dtsg, jazoest, lsd, profile_id)

            # Check the JSON directly
            if "errors" in res_json:
                print(f"❌ [{profile_dir}] GraphQL Rejected the Request! FB says:")
                print(json.dumps(res_json["errors"], indent=2))
                return False
            elif "data" in res_json:
                print(f"✅ [{profile_dir}] Automation finished! Action '{action}' successful via API.")

                # Database insertion logic for Drafts
                if action == "draft":
                    try:
                        # FB GraphQL response structure varies slightly, attempt to parse listing ID
                        listing_id = None
                        data_node = res_json.get("data", {}).get("marketplace_listing_create", {})

                        if data_node and "marketplace_listing" in data_node:
                            listing_id = data_node["marketplace_listing"].get("id")

                        # If we couldn't parse the ID directly, use a timestamp dummy
                        if not listing_id:
                            listing_id = f"DRAFT_{int(time.time())}"

                        draft_url = f"https://web.facebook.com/marketplace/item/{listing_id}"
                        db.insert_draft(profile_dir, listing_id, draft_url, current_title, "Drafted (API)")
                        print(f"✅ [{profile_dir}] Draft URL saved to DB: {draft_url}")
                    except Exception as e:
                        print(f"⚠️ [{profile_dir}] Could not save draft to DB: {e}")

                return True
            else:
                print(f"⚠️ [{profile_dir}] Unknown response format.")
                print(res_json)
                return False
        except Exception as e:
            print(f"⚠️ [{profile_dir}] Error during API listing: {e}")
            return False

    def _get_session_data(self, driver):
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

    def _api_upload_image(self, session, image_path, fb_dtsg, jazoest, lsd, profile_id):
        """Uploads a single image directly via API and returns its photo_id."""
        url = f"https://upload.facebook.com/ajax/react_composer/attachments/photo/upload?av={profile_id}&__user={profile_id}&__a=1&fb_dtsg={fb_dtsg}&jazoest={jazoest}&lsd={lsd}"
        data = {
            "fb_dtsg": fb_dtsg,
            "qn": "comet_marketplace_composer",
            "target_id": "355209128917923",
            "source": "8",
            "profile_id": profile_id,
            "waterfallxapp": "comet",
            "upload_id": "1024"
        }
        try:
            with open(image_path, 'rb') as f:
                files = {'farr': (image_path.split('/')[-1].split('\\')[-1], f, 'image/jpeg')}
                response = session.post(url, data=data, files=files)
            raw_text = response.text.replace('for (;;);', '').strip()
            clean_res = json.loads(raw_text)
            payload = clean_res.get('payload')
            if payload and isinstance(payload, dict):
                photo_id = payload.get('fbid') or payload.get('photoID')
                if photo_id:
                    return str(photo_id)
            print(f"❌ FB rejected the image. Raw Response: {raw_text}")
            return None
        except Exception as e:
            print(f"❌ Failed to parse FB response: {e}")
            return None

    def _prepare_graphql_variables(self, template_data, photo_ids, profile_id, is_draft=True):
        """Prepares the variables JSON for the GraphQL request."""
        condition_map = {
            "New": "new", "Used - Like New": "used_like_new",
            "Used - Good": "used_good", "Used - Fair": "used_fair"
        }
        condition_val = condition_map.get(template_data.get('condition'), "used_good")
        cat_id = self.CATEGORY_MAP.get(template_data.get('category'), "1569171756675761")
        delivery_types = ["IN_PERSON"]
        if template_data.get('door_meetup'):
            delivery_types.append("DOOR_DROPOFF")
        photo_ids = [str(pid) for pid in photo_ids]

        draft_type = "COMMERCE_SELL_OPTIONS" if is_draft else None
        variables = {
            "input": {
                "actor_id": str(profile_id),
                "client_mutation_id": str(random.randint(1, 20)),
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
                        "description": {"text": str(template_data.get('description') or template_data.get('desc') or '')},
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
                        "quantity": -1 if template_data.get('availability') == "List as Single Item" else 99,
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
        if draft_type:
            variables["input"]["data"]["common"]["draft_type"] = draft_type
        return variables

    def _execute_graphql_mutation(self, driver, variables, fb_dtsg, jazoest, lsd, profile_id):
        """Injects a native JS fetch request into the browser with full Form Data sync."""
        data = {
            "av": profile_id,
            "__user": profile_id,
            "__a": "1",
            "__req": "2a",
            "__aaid": "0",
            "fb_dtsg": fb_dtsg,
            "jazoest": jazoest,
            "lsd": lsd,
            "__comet_req": "15",
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
        js_code = """
        var done = arguments[arguments.length - 1];
        var base_payload = arguments[0];
        var passed_lsd = arguments[1];
        var sd = {};
        try { sd = require('SiteData'); } catch(e) {}
        var body_str = base_payload;
        if(sd.revision) body_str += '&__rev=' + sd.revision;
        if(sd.hsi) body_str += '&__hsi=' + sd.hsi;
        if(sd.__spin_r) body_str += '&__spin_r=' + sd.__spin_r;
        if(sd.__spin_b) body_str += '&__spin_b=' + sd.__spin_b;
        if(sd.__spin_t) body_str += '&__spin_t=' + sd.__spin_t;
        fetch("https://web.facebook.com/api/graphql/", {
            method: "POST",
            credentials: "same-origin",
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
            const cleanText = text.replace('for (;;);', '').trim();
            done(JSON.parse(cleanText));
        })
        .catch(error => done({"errors": [{"message": "JS Fetch failed: " + error}]}));
        """
        response_json = driver.execute_async_script(js_code, encoded_data, lsd)
        return response_json

    def draft_listing(self, driver, template_data, photo_ids, fb_dtsg, jazoest, lsd, profile_id):
        """Saves listing as a draft."""
        print(f"🚀 [{profile_id}] Saving listing as DRAFT via Browser XHR Injection...")
        variables = self._prepare_graphql_variables(template_data, photo_ids, profile_id, is_draft=True)
        return self._execute_graphql_mutation(driver, variables, fb_dtsg, jazoest, lsd, profile_id)

    def publish_listing(self, driver, template_data, photo_ids, fb_dtsg, jazoest, lsd, profile_id):
        """Publishes listing directly."""
        print(f"🚀 [{profile_id}] PUBLISHING listing directly via Browser XHR Injection...")
        variables = self._prepare_graphql_variables(template_data, photo_ids, profile_id, is_draft=False)
        return self._execute_graphql_mutation(driver, variables, fb_dtsg, jazoest, lsd, profile_id)

def perform_api_listing(driver, details, p_name, state):
    """Entry point for worker.py to use Ultra Fast Listing"""
    lister = MarketplaceLister()

    # Check if we should randomize location, titles etc.
    original_images = details.get('images', [])
    drafts_count = int(details.get("drafts_multiplier", 1))

    # Handle Location extraction (if randomly chosen from file)
    location_to_use = details.get('location', '')
    if details.get('loc_type') == 'file' and details.get('loc_file'):
        try:
            with open(details['loc_file'], 'r') as f:
                locs = [l.strip() for l in f.readlines() if l.strip()]
            if locs:
                location_to_use = random.choice(locs) if details.get('loc_random') else locs[0]
        except:
            pass

    details['location'] = location_to_use

    # Handle title strategies
    titles_list = []
    if details.get('title_type') == 'file' and details.get('title_file'):
        try:
            with open(details['title_file'], 'r') as f:
                titles_list = [l.strip() for l in f.readlines() if l.strip()]
        except:
            titles_list = [details.get("title", "Listing")]
    else:
        titles_list = [details.get("title", "Listing")]

    action = "publish" if details.get("direct_publish") else "draft"

    for i in range(drafts_count):
        if state.GLOBAL_STOP:
            break

        current_title = random.choice(titles_list) if titles_list else "Listing"

        current_images = original_images.copy()
        if drafts_count > 1:
            random.shuffle(current_images)

        # Update details clone for this run
        run_details = details.copy()
        run_details['images'] = current_images

        success = lister.create_listing(driver, p_name, run_details, action=action, current_title=current_title)

        if success:
            state.update_status(p_name, f"✅ API {action.capitalize()}ed")
        else:
            state.update_status(p_name, f"❌ API {action.capitalize()} Failed")

        if i < drafts_count - 1:
            time.sleep(random.uniform(5, 10))

    return True
