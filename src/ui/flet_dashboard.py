import flet as ft
import datetime
import os
import sys
import threading
import time
import json
import psutil
import src.state as state
from src.utils.system_utils import check_login_status, smart_cleanup, get_or_create_fingerprint, force_delete_dir, play_success_sound, force_kill_browser
from src.automation.worker import worker_task
from concurrent.futures import ThreadPoolExecutor

def main(page: ft.Page):
    # ==========================================
    # 1. APP CONFIGURATION & STYLING
    # ==========================================
    page.title = "Abiz Global Enterprise Dashboard"
    page.window.width = 1350
    page.window.height = 850
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = "#F4F7FC"

    C_PRIMARY = "#3182CE"
    C_SIDEBAR = "#FFFFFF"
    C_TEXT_DARK = "#2D3748"
    C_TEXT_MUTED = "#718096"
    C_ACCENT = "#38B2AC"
    C_DANGER = "#E53E3E"
    C_WARNING = "#DD6B20"

    border_1px = ft.Border(top=ft.BorderSide(1, "#E2E8F0"), right=ft.BorderSide(1, "#E2E8F0"), bottom=ft.BorderSide(1, "#E2E8F0"), left=ft.BorderSide(1, "#E2E8F0"))
    border_right_only = ft.Border(right=ft.BorderSide(1, "#E2E8F0"))
    border_bottom_only = ft.Border(bottom=ft.BorderSide(1, "#E2E8F0"))

    app_state = {
        "profile_vars": {},
        "selected_images": [],
        "title_file": None,
        "desc_file": None,
        "loc_file": None,
        "schedule_time": None
    }

    # ==========================================
    # 2. CORE UI HELPERS
    # ==========================================
    def show_dialog(dlg):
        if dlg not in page.overlay: page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def hide_dialog(dlg):
        dlg.open = False
        page.update()

    def show_alert(title, message, alert_type="info"):
        color = C_ACCENT if alert_type == "success" else C_DANGER if alert_type == "error" else C_PRIMARY
        dlg = ft.AlertDialog(shape=ft.RoundedRectangleBorder(radius=12), title=ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, color=color), ft.Text(title, color=C_TEXT_DARK, weight=ft.FontWeight.BOLD)]), content=ft.Text(message, color=C_TEXT_MUTED), actions=[modern_btn("OK", bgcolor=color, on_click=lambda e: hide_dialog(dlg))])
        show_dialog(dlg)

    def modern_btn(text, icon=None, bgcolor=C_PRIMARY, text_color=ft.Colors.WHITE, on_click=None, width=None, height=38, expand=False):
        row_content = []
        if icon: row_content.append(ft.Icon(icon, color=text_color, size=16))
        if text: row_content.append(ft.Text(text, color=text_color, weight=ft.FontWeight.BOLD, size=13))
        return ft.Container(content=ft.Row(row_content, alignment=ft.MainAxisAlignment.CENTER, spacing=6), bgcolor=bgcolor, padding=ft.Padding(left=15, top=5, right=15, bottom=5), border_radius=6, width=width, height=height, expand=expand, ink=True, alignment=ft.Alignment(0, 0), on_click=on_click if on_click else lambda e: None)

    def icon_btn(icon, color, tooltip, on_click=None):
        return ft.Container(content=ft.Icon(icon, size=18, color=color), bgcolor=ft.Colors.with_opacity(0.1, color), padding=ft.Padding(left=8, top=8, right=8, bottom=8), border_radius=6, tooltip=tooltip, ink=True, on_click=on_click if on_click else lambda e: None)

    def get_selected_profiles():
        selected = [p for p, var in app_state["profile_vars"].items() if var.value]
        if not selected: show_alert("Selection Required", "Please select at least one profile via scanner checkboxes.", "error")
        return selected

    lbl_qcount = ft.Text("0 tasks queued", color=C_TEXT_MUTED)
    lbl_global_status = ft.Text("Idle", weight=ft.FontWeight.BOLD, color=C_PRIMARY)
    progress_bar = ft.ProgressBar(value=0, color=C_ACCENT, bgcolor="#E2E8F0")

    def update_queue_display():
        lbl_qcount.value = f"{len(state.TASK_QUEUE)} tasks queued"
        page.update()

    def add_to_queue(profiles, task_type, details=None):
        for p in profiles: state.TASK_QUEUE.append((p, task_type, details, None, None))
        update_queue_display()
        show_alert("Added to Queue", f"{len(profiles)} tasks added to pending automated queue.", "success")

    def execute_master_queue(threads):
        state.GLOBAL_STOP = False
        total_tasks = len(state.TASK_QUEUE)
        completed = 0
        start_time = time.time()
        lbl_global_status.value = f"Starting {total_tasks} tasks..."
        page.update()

        def progress_callback(p_name=None, t_type=None):
            nonlocal completed
            completed += 1
            elapsed = time.time() - start_time
            if completed > 0:
                eta = int((elapsed / completed) * (total_tasks - completed))
                eta_str = f"{eta}s" if eta < 60 else f"{eta//60}m {eta%60}s"
            else: eta_str = "..."

            progress_bar.value = completed / total_tasks
            lbl_global_status.value = f"Progress: {completed}/{total_tasks} | ETA: {eta_str} | Just finished: {p_name}"
            page.update()

        with ThreadPoolExecutor(max_workers=threads) as executor:
            for task in state.TASK_QUEUE:
                if state.GLOBAL_STOP: break
                pn, tt = task[0], task[1]
                executor.submit(worker_task, pn, tt, task[2], task[3], task[4], lambda pn=pn, tt=tt: progress_callback(pn, tt))

        if not state.GLOBAL_STOP:
            play_success_sound()
            show_alert("Execution Complete", "All queued tasks finished successfully!", "success")
        state.TASK_QUEUE.clear()
        progress_bar.value = 0
        lbl_global_status.value = "Idle"
        update_queue_display()
        refresh_profiles()

    def run_queue_btn_click(e):
        if not state.TASK_QUEUE:
            show_alert("Queue Empty", "Add tasks to the queue first before running.", "error")
            return
        threads_input = ft.TextField(label="Parallel Threads (1-10)", value="3", width=200)
        def on_submit(e):
            try:
                threads = int(threads_input.value)
                hide_dialog(concurrency_dialog)
                threading.Thread(target=execute_master_queue, args=(threads,), daemon=True).start()
            except ValueError: show_alert("Invalid Input", "Please enter a valid integer for threads.", "error")
        concurrency_dialog = ft.AlertDialog(title=ft.Text("Concurrency"), content=threads_input, actions=[modern_btn("Run", on_click=on_submit)])
        show_dialog(concurrency_dialog)

    def emergency_stop(e):
        state.GLOBAL_STOP = True
        for driver in state.ACTIVE_DRIVERS: force_kill_browser(driver)
        state.ACTIVE_DRIVERS.clear()
        show_alert("Stopped", "Automation halted forcefully. Browsers killed.", "error")
        update_queue_display()

    # ==========================================
    # 4. POPUPS & DIALOGS
    # ==========================================
    warning_dialog = ft.AlertDialog(shape=ft.RoundedRectangleBorder(radius=12), content_padding=ft.Padding(left=20, top=20, right=20, bottom=10), title=ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color=C_DANGER, size=28), ft.Text("Action Blocked", color=C_TEXT_DARK, weight=ft.FontWeight.BOLD)]), content=ft.Text("Please select at least one profile to run the master queue.", color=C_TEXT_MUTED, size=14), actions=[modern_btn("Understood", bgcolor=C_DANGER, on_click=lambda e: hide_dialog(warning_dialog))])

    # Schedule Dialog
    selected_date_label = ft.Text("No Date Selected", color=C_TEXT_DARK, weight=ft.FontWeight.BOLD, size=15)
    def handle_date_change(e):
        if date_picker.value:
            selected_date_label.value = date_picker.value.strftime("%B %d, %Y")
            selected_date_label.color = C_PRIMARY
        page.update()

    date_picker = ft.DatePicker(on_change=handle_date_change, first_date=datetime.datetime.now())
    page.overlay.append(date_picker)

    hr_drop = ft.Dropdown(options=[ft.dropdown.Option(f"{i:02d}:00") for i in range(24)], width=150, text_size=13, border_color="#CBD5E0", border_radius=6, content_padding=10, color=ft.Colors.BLACK87)
    rep_drop = ft.Dropdown(options=[ft.dropdown.Option("None"), ft.dropdown.Option("Hourly"), ft.dropdown.Option("Daily"), ft.dropdown.Option("Weekly")], value="None", width=150, text_size=13, border_color="#CBD5E0", border_radius=6, content_padding=10, color=ft.Colors.BLACK87)

    def on_schedule_save(e):
        if not date_picker.value or not hr_drop.value:
            show_alert("Error", "Please select a valid date and time.", "error")
            return
        date_str = date_picker.value.strftime("%Y-%m-%d")
        time_str = hr_drop.value
        try:
            target_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            if target_dt < datetime.datetime.now():
                show_alert("Invalid Time", "Target time is in the past!", "error")
                return
            app_state["schedule_config"] = {"datetime": target_dt, "repeat": rep_drop.value}

            # Start background schedule waiter
            def schedule_waiter():
                queue_snapshot = list(state.TASK_QUEUE)
                while True:
                    if state.GLOBAL_STOP: return
                    if datetime.datetime.now() >= app_state["schedule_config"]["datetime"]:
                        state.TASK_QUEUE.clear()
                        state.TASK_QUEUE.extend(queue_snapshot)
                        execute_master_queue(3) # Defaulting to 3 threads for scheduled tasks

                        rmode = app_state["schedule_config"]["repeat"]
                        if rmode == "Hourly": app_state["schedule_config"]["datetime"] += datetime.timedelta(hours=1)
                        elif rmode == "Daily": app_state["schedule_config"]["datetime"] += datetime.timedelta(days=1)
                        elif rmode == "Weekly": app_state["schedule_config"]["datetime"] += datetime.timedelta(days=7)
                        else: break
                    time.sleep(5)
            threading.Thread(target=schedule_waiter, daemon=True).start()
            hide_dialog(scheduler_dialog)
            show_alert("Scheduled", f"Queue scheduled to run at {target_dt.strftime('%Y-%m-%d %H:%M')}", "success")
        except Exception as err:
            show_alert("Error", f"Failed: {err}", "error")

    scheduler_dialog = ft.AlertDialog(
        shape=ft.RoundedRectangleBorder(radius=12), title=ft.Text("Schedule Execution", weight=ft.FontWeight.BOLD, color=C_TEXT_DARK, size=18),
        content=ft.Container(width=350, content=ft.Column([
                ft.Container(content=ft.Column([ft.Icon(ft.Icons.CALENDAR_MONTH, size=35, color=C_TEXT_MUTED), selected_date_label, modern_btn("Open Calendar", bgcolor="#EDF2F7", text_color=C_TEXT_DARK, height=32, on_click=lambda e: setattr(date_picker, 'open', True) or page.update())], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10), height=150, bgcolor="#F8FAFC", border_radius=8, border=border_1px, alignment=ft.Alignment(0,0)),
                ft.Container(height=10), ft.Row([ft.Text("Time (24H):", weight=ft.FontWeight.BOLD, color=C_TEXT_DARK), hr_drop], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("Repeat:", weight=ft.FontWeight.BOLD, color=C_TEXT_DARK), rep_drop], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], tight=True)),
        actions=[ft.Container(content=ft.Row([modern_btn("Cancel", bgcolor="#EDF2F7", text_color=C_TEXT_DARK, on_click=lambda e: hide_dialog(scheduler_dialog), expand=True), modern_btn("Save Schedule", bgcolor=C_ACCENT, icon=ft.Icons.CHECK, on_click=on_schedule_save, expand=True)], spacing=10), padding=ft.Padding(left=15, top=0, right=15, bottom=10))]
    )

    # Listing Configurator Dialog (Complex Form)
    def form_label(text): return ft.Text(text, weight=ft.FontWeight.BOLD, size=13, color=C_TEXT_DARK)

    marketplace_categories = ["Tools", "Furniture", "Household", "Garden", "Appliances", "Video Games", "Books, Movies & Music", "Bags & Luggage", "Women's clothing & shoes", "Men's clothing & shoes", "Jewelry & Accessories", "Health & beauty", "Pet Supplies", "Baby & kids", "Toys & Games", "Electronics & computers", "Mobile phones", "Bicycles", "Arts & Crafts", "Sports & Outdoors", "Auto parts", "Musical Instruments", "Antiques & Collectibles", "Garage Sale", "Miscellaneous"]
    marketplace_conditions = ["New", "Used - Like New", "Used - Good", "Used - Fair"]

    title_fp = ft.FilePicker()
    page.overlay.append(title_fp)

    def browse_titles(e):
        files = title_fp.pick_files(allowed_extensions=["txt"])
        if files:
            app_state["title_file"] = files[0].path
            lbl_title_file.value = f"Loaded: {files[0].name}"
            title_strat.value = "auto"
            page.update()

    title_strat = ft.RadioGroup(value="manual", content=ft.Column([
        ft.Radio(value="manual", label="Manual Single Title", label_style=ft.TextStyle(size=13, color=C_TEXT_DARK)),
        title_ent := ft.TextField(hint_text="Enter product title...", height=40, text_size=13, border_radius=6, border_color="#CBD5E0", content_padding=10, color=ft.Colors.BLACK87),
        ft.Container(height=5),
        ft.Radio(value="auto", label="Auto-Randomize Titles from list (.txt)", label_style=ft.TextStyle(size=13, color=C_TEXT_DARK)),
        ft.Row([modern_btn("Browse Titles File (.txt)", bgcolor="#EDF2F7", text_color=C_TEXT_DARK, height=32, on_click=browse_titles), lbl_title_file := ft.Text("Status: Manual Mode", color=C_PRIMARY, size=12, italic=True)]),
    ], spacing=2))

    drafts_mult_ent = ft.TextField(value="1", width=120, height=40, text_size=13, border_radius=6, border_color="#CBD5E0", content_padding=10, color=ft.Colors.BLACK87)
    price_ent = ft.TextField(hint_text="e.g. 50", width=120, height=40, text_size=13, border_radius=6, border_color="#CBD5E0", content_padding=10, color=ft.Colors.BLACK87)

    lbl_img_count = ft.Text("0 Assets Selected", color=C_PRIMARY, weight=ft.FontWeight.BOLD, size=13)
    imgs_fp = ft.FilePicker()
    page.overlay.append(imgs_fp)

    def pick_images(e):
        files = imgs_fp.pick_files(allow_multiple=True)
        if files:
            app_state["selected_images"].extend([f.path for f in files])
            lbl_img_count.value = f"{len(app_state['selected_images'])} Assets Selected"
            page.update()

    def clear_imgs(e):
        app_state["selected_images"].clear()
        lbl_img_count.value = "0 Assets Selected"
        page.update()

    tab1_basic = ft.Container(padding=ft.Padding(left=0, top=15, right=0, bottom=10), content=ft.Column([form_label("Product Title Strategy:"), title_strat, ft.Container(height=10), ft.Row([ft.Column([form_label("Drafts Multiplier:"), ft.Text("How many drafts per profile?", size=11, color=C_TEXT_MUTED), drafts_mult_ent], expand=1), ft.Column([form_label("Product Price ($):"), ft.Text("Listing price", size=11, color=C_TEXT_MUTED), price_ent], expand=1)]), ft.Container(height=10), ft.Row([form_label("Product Visual Assets (Multiple Images):"), modern_btn("Clear All", bgcolor="#FFF5F5", text_color=C_DANGER, height=28, on_click=clear_imgs)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(content=ft.Column([ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE, color=C_PRIMARY, size=32), lbl_img_count], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), height=120, border=ft.Border(*[ft.BorderSide(2, "#E2E8F0")]*4), border_radius=8, alignment=ft.Alignment(0,0), ink=True, bgcolor="#F8FAFC", on_click=pick_images)], scroll=ft.ScrollMode.AUTO))

    cat_var = ft.Dropdown(options=[ft.dropdown.Option(cat) for cat in marketplace_categories], value="Tools", height=45, text_size=13, border_color="#CBD5E0", border_radius=6, color=ft.Colors.BLACK87)
    cond_var = ft.Dropdown(options=[ft.dropdown.Option(cond) for cond in marketplace_conditions], value="New", height=45, text_size=13, border_color="#CBD5E0", border_radius=6, color=ft.Colors.BLACK87)

    desc_fp = ft.FilePicker()
    page.overlay.append(desc_fp)

    def browse_desc(e):
        files = desc_fp.pick_files(allowed_extensions=["txt"])
        if files:
            app_state["desc_file"] = files[0].path
            lbl_desc_file.value = f"Loaded: {files[0].name}"
            desc_strat.value = "auto"
            page.update()

    desc_strat = ft.RadioGroup(value="manual", content=ft.Column([
        ft.Radio(value="manual", label="Manual Single Description", label_style=ft.TextStyle(size=13, color=C_TEXT_DARK)),
        desc_ent := ft.TextField(hint_text="Write a detailed description...", multiline=True, min_lines=4, max_lines=4, text_size=13, border_color="#CBD5E0", border_radius=6, color=ft.Colors.BLACK87),
        ft.Radio(value="auto", label="Auto-Randomize Descriptions (.txt) [Comma separated]:", label_style=ft.TextStyle(size=13, color=C_TEXT_DARK)),
        ft.Row([modern_btn("Browse Descriptions File (.txt)", bgcolor="#EDF2F7", text_color=C_TEXT_DARK, height=32, on_click=browse_desc), lbl_desc_file := ft.Text("Status: Manual Mode", color=C_PRIMARY, size=12, italic=True)]),
    ], spacing=2))

    tags_ent = ft.TextField(hint_text="e.g. quartz, minerals, leather, wholesale...", height=40, text_size=13, border_color="#CBD5E0", border_radius=6, content_padding=10, color=ft.Colors.BLACK87)
    tab2_taxonomy = ft.Container(padding=ft.Padding(left=0, top=15, right=0, bottom=10), content=ft.Column([form_label("Marketplace Category:"), cat_var, ft.Container(height=10), form_label("Condition Status:"), cond_var, ft.Container(height=10), form_label("Listing Description Strategy:"), desc_strat, ft.Container(height=10), form_label("Search Tags (Comma separated):"), tags_ent], scroll=ft.ScrollMode.AUTO))

    loc_fp = ft.FilePicker()
    page.overlay.append(loc_fp)

    def browse_loc(e):
        files = loc_fp.pick_files(allowed_extensions=["txt"])
        if files:
            app_state["loc_file"] = files[0].path
            lbl_loc_file.value = f"Loaded: {files[0].name}"
            loc_strat.value = "auto"
            page.update()

    loc_strat = ft.RadioGroup(value="manual", content=ft.Column([
        ft.Radio(value="manual", label="Manual City Entry:", label_style=ft.TextStyle(size=13, color=C_TEXT_DARK)),
        loc_ent := ft.TextField(hint_text="e.g. New York, NY", height=40, text_size=13, border_radius=6, border_color="#CBD5E0", content_padding=10, color=ft.Colors.BLACK87),
        ft.Radio(value="auto", label="Auto-Randomize from list (.txt) per profile", label_style=ft.TextStyle(size=13, color=C_TEXT_DARK)),
        ft.Row([modern_btn("Browse Locations File (.txt)", bgcolor="#EDF2F7", text_color=C_TEXT_DARK, height=32, on_click=browse_loc), lbl_loc_file := ft.Text("Status: Manual Mode", color=C_PRIMARY, size=12, italic=True)]),
    ], spacing=2))

    avail_var = ft.Dropdown(options=[ft.dropdown.Option("List as Single Item"), ft.dropdown.Option("List as In-Stock")], value="List as Single Item", height=40, text_size=13, border_color="#CBD5E0", border_radius=6, color=ft.Colors.BLACK87)
    meet_pub = ft.Checkbox(label="Public Meetup", label_style=ft.TextStyle(size=12, color=C_TEXT_DARK))
    meet_door = ft.Checkbox(label="Door Pickup", label_style=ft.TextStyle(size=12, color=C_TEXT_DARK))

    engine_strat = ft.RadioGroup(value="ui", content=ft.Column([ft.Radio(value="ui", label="Normal UI Automation (Standard)", label_style=ft.TextStyle(size=12, color=C_TEXT_DARK)), ft.Radio(value="api", label="Ultra Fast Injection (API Mode)", label_style=ft.TextStyle(size=12, color=C_TEXT_DARK))], spacing=2))
    direct_pub_var = ft.Checkbox(label="Publish Directly (Skip Drafts)", label_style=ft.TextStyle(color=C_DANGER, weight=ft.FontWeight.BOLD, size=12))

    config_fp = ft.FilePicker()
    save_fp = ft.FilePicker()
    page.overlay.extend([config_fp, save_fp])

    def load_config_template(e):
        files = config_fp.pick_files(allowed_extensions=["json"])
        if files:
            try:
                with open(files[0].path, 'r') as f:
                    details = json.load(f)
                title_ent.value = details.get("title", "")
                price_ent.value = details.get("price", "")
                cat_var.value = details.get("category", "Tools")
                cond_var.value = details.get("condition", "New")
                avail_var.value = details.get("avail", "List as Single Item")
                desc_ent.value = details.get("desc", "")
                tags_ent.value = details.get("tags", "")

                title_strat.value = details.get("title_strat", "manual")
                app_state["title_file"] = details.get("title_f", "")
                if app_state["title_file"]: lbl_title_file.value = f"Loaded: {os.path.basename(app_state['title_file'])}"

                desc_strat.value = details.get("desc_strat", "manual")
                app_state["desc_file"] = details.get("desc_f", "")
                if app_state["desc_file"]: lbl_desc_file.value = f"Loaded: {os.path.basename(app_state['desc_file'])}"

                loc_strat.value = details.get("loc_strat", "manual")
                loc_ent.value = details.get("loc", "")
                app_state["loc_file"] = details.get("loc_f", "")
                if app_state["loc_file"]: lbl_loc_file.value = f"Loaded: {os.path.basename(app_state['loc_file'])}"

                meet_pub.value = details.get("meet_p", False)
                meet_door.value = details.get("door_p", False)
                direct_pub_var.value = details.get("direct_publish", False)
                engine_strat.value = details.get("engine", "normal")
                drafts_mult_ent.value = details.get("drafts_multiplier", "1")

                app_state["selected_images"] = details.get("imgs", [])
                lbl_img_count.value = f"{len(app_state['selected_images'])} Assets Selected"
                page.update()
            except Exception as err:
                show_alert("Error", f"Failed to load config: {err}", "error")

    def save_config_template(e):
        path = save_fp.save_file(dialog_title="Save Config As", allowed_extensions=["json"], file_name="listing_config.json")
        if path:
            path = path if path.endswith('.json') else f"{path}.json"
            details = {
                "title": title_ent.value, "price": price_ent.value, "category": cat_var.value, "condition": cond_var.value,
                "avail": avail_var.value, "desc": desc_ent.value, "tags": tags_ent.value, "loc_strat": loc_strat.value,
                "loc": loc_ent.value, "loc_f": app_state["loc_file"], "meet_p": meet_pub.value,
                "door_p": meet_door.value, "imgs": app_state["selected_images"], "direct_publish": direct_pub_var.value,
                "engine": engine_strat.value,
                "title_strat": title_strat.value, "title_f": app_state["title_file"],
                "desc_strat": desc_strat.value, "desc_f": app_state["desc_file"],
                "drafts_multiplier": drafts_mult_ent.value
            }
            try:
                with open(path, 'w') as f: json.dump(details, f)
                show_alert("Saved", "Configuration saved successfully.", "success")
            except Exception as err:
                show_alert("Error", f"Failed to save config: {err}", "error")

    tab3_settings = ft.Container(padding=ft.Padding(left=0, top=15, right=0, bottom=10), content=ft.Column([form_label("Geographic Location Strategy:"), loc_strat, ft.Container(height=15), ft.Row([ft.Column([form_label("Fulfillment Preferences:"), avail_var, ft.Row([meet_pub, meet_door])], expand=1), ft.Column([form_label("Execution Mode & Engine:"), engine_strat, direct_pub_var], expand=1)]), ft.Divider(color="#E2E8F0"), form_label("Templates Management:"), ft.Row([modern_btn("Load Config Template", icon=ft.Icons.FOLDER_OPEN, bgcolor="#805AD5", expand=True, on_click=load_config_template), modern_btn("Save Current Config", icon=ft.Icons.SAVE, bgcolor=C_WARNING, expand=True, on_click=save_config_template)])], scroll=ft.ScrollMode.AUTO))
    config_content_area = ft.Container(content=tab1_basic, expand=True)
    def switch_config_tab(e, index):
        config_content_area.content = [tab1_basic, tab2_taxonomy, tab3_settings][index]
        for i, btn in enumerate(config_tabs_row.controls):
            btn.border = ft.Border(bottom=ft.BorderSide(3, C_PRIMARY if i == index else ft.Colors.TRANSPARENT))
            btn.content.color = C_PRIMARY if i == index else C_TEXT_MUTED
        page.update()
    def create_tab_header(text, index, active=False): return ft.Container(content=ft.Text(text, weight=ft.FontWeight.BOLD, color=C_PRIMARY if active else C_TEXT_MUTED, size=14), padding=ft.Padding(left=15, top=10, right=15, bottom=10), border=ft.Border(bottom=ft.BorderSide(3, C_PRIMARY if active else ft.Colors.TRANSPARENT)), ink=True, on_click=lambda e: switch_config_tab(e, index))
    config_tabs_row = ft.Row([create_tab_header("Basic Configuration", 0, True), create_tab_header("Taxonomy & Description", 1), create_tab_header("Settings & Deploy", 2)], spacing=10)

    def queue_listing(e):
        selected = get_selected_profiles()
        if not selected: return
        details = {
            "title": title_ent.value, "title_type": "file" if title_strat.value == "auto" else "manual", "title_file": app_state["title_file"],
            "price": price_ent.value, "category": cat_var.value, "condition": cond_var.value, "availability": avail_var.value,
            "desc": desc_ent.value, "desc_type": "file" if desc_strat.value == "auto" else "manual", "desc_file": app_state["desc_file"],
            "tags": tags_ent.value, "public_meetup": meet_pub.value, "door_pickup": meet_door.value, "images": app_state["selected_images"].copy(),
            "direct_publish": direct_pub_var.value, "engine": "api" if engine_strat.value == "api" else "normal",
            "location": loc_ent.value, "loc_type": "file" if loc_strat.value == "auto" else "manual", "loc_file": app_state["loc_file"],
            "loc_random": True, "drafts_multiplier": int(drafts_mult_ent.value) if drafts_mult_ent.value.isdigit() else 1
        }
        hide_dialog(config_dialog)
        add_to_queue(selected, "listing", details)

    config_dialog = ft.AlertDialog(shape=ft.RoundedRectangleBorder(radius=12), content_padding=ft.Padding(left=25, top=20, right=25, bottom=10), title=ft.Row([ft.Icon(ft.Icons.SETTINGS_APPLICATIONS, color=C_PRIMARY, size=26), ft.Text("Listing Deployment Configurator", weight=ft.FontWeight.W_800, color=C_TEXT_DARK)]), content=ft.Container(width=800, height=500, content=ft.Column([ft.Container(content=config_tabs_row, border=border_bottom_only), config_content_area], spacing=0)), actions=[ft.Container(content=ft.Row([modern_btn("Close", bgcolor="#EDF2F7", text_color=C_TEXT_DARK, on_click=lambda e: hide_dialog(config_dialog), width=100), modern_btn("+ ADD TO MULTI-DEPLOY QUEUE", icon=ft.Icons.QUEUE, bgcolor="#38A169", on_click=queue_listing)], alignment=ft.MainAxisAlignment.END, spacing=10), padding=ft.Padding(left=0, top=0, right=10, bottom=10))])

    # ==========================================
    # 5. SIDEBAR NAVIGATION
    # ==========================================
    def sidebar_item(text, icon, active=False, on_click=None): return ft.Container(content=ft.Row([ft.Icon(icon, color=C_PRIMARY if active else C_TEXT_MUTED, size=20), ft.Text(text, color=C_PRIMARY if active else C_TEXT_DARK, weight=ft.FontWeight.BOLD if active else ft.FontWeight.W_500, size=13)]), bgcolor="#EBF8FF" if active else ft.Colors.TRANSPARENT, padding=ft.Padding(left=20, top=12, right=20, bottom=12), border_radius=8, ink=True, on_click=on_click if on_click else lambda e: None)

    def prepare_manual_queued(e):
        selected = get_selected_profiles()
        if not selected: return
        def on_submit(e):
            url = "https://web.facebook.com" if url_strat.value == "fb" else "about:blank" if url_strat.value == "blank" else url_ent.value
            hide_dialog(manual_dlg)
            add_to_queue(selected, "manual", {"url": url})
        url_strat = ft.RadioGroup(value="fb", content=ft.Column([ft.Radio(value="fb", label="Facebook Default"), ft.Radio(value="blank", label="Blank New Tab"), ft.Row([ft.Radio(value="custom", label="Custom URL:"), url_ent := ft.TextField(width=200)])]))
        manual_dlg = ft.AlertDialog(title=ft.Text("Manual Launch Config", weight=ft.FontWeight.BOLD), content=url_strat, actions=[modern_btn("Add to Queue", on_click=on_submit)])
        show_dialog(manual_dlg)

    login_fp = ft.FilePicker()
    page.overlay.append(login_fp)

    def prepare_login_queued(e):
        selected = get_selected_profiles()
        if not selected: return
        files = login_fp.pick_files(allowed_extensions=["txt"])
        if files:
            with open(files[0].path, "r") as f:
                ids = [line.strip().split(",") for line in f if "," in line]
            for i, p_name in enumerate(selected):
                if i < len(ids): state.TASK_QUEUE.append((p_name, "login", None, ids[i][0], ids[i][1]))
            update_queue_display()
            show_alert("Added to Queue", "Multi-login queued.", "success")

    def prepare_human_activity_queued(e):
        selected = get_selected_profiles()
        if not selected: return
        mins_input = ft.TextField(label="Duration (minutes)", value="5", width=200)
        def on_submit(e):
            try:
                mins = int(mins_input.value)
                hide_dialog(hum_dlg)
                add_to_queue(selected, "human_activity", {"duration_minutes": mins})
            except: show_alert("Error", "Invalid number", "error")
        hum_dlg = ft.AlertDialog(title=ft.Text("Human Activity"), content=mins_input, actions=[modern_btn("Run", on_click=on_submit)])
        show_dialog(hum_dlg)

    def prepare_publish_drafts(e):
        selected = get_selected_profiles()
        if not selected: return
        tabs_input = ft.TextField(label="Tabs to open per profile", value="5", width=200)
        def on_submit(e):
            try:
                tabs = int(tabs_input.value)
                hide_dialog(pub_dlg)
                add_to_queue(selected, "publish_drafts", {"tabs_count": tabs})
            except: show_alert("Error", "Invalid number", "error")
        pub_dlg = ft.AlertDialog(title=ft.Text("Publish Drafts"), content=tabs_input, actions=[modern_btn("Run", on_click=on_submit)])
        show_dialog(pub_dlg)

    def bulk_health_check(e):
        selected = get_selected_profiles()
        if not selected: return
        add_to_queue(selected, "health_check")

    folder_fp = ft.FilePicker()
    page.overlay.append(folder_fp)

    def bulk_create_profiles(e):
        count_input = ft.TextField(label="Number of profiles to create", value="5", width=200)
        chrome_exe = ft.TextField(label="Path to Chrome.exe (for shortcuts)", value=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        def on_submit(e):
            try:
                count = int(count_input.value)
                hide_dialog(create_dlg)

                shortcut_dir = folder_fp.get_directory_path(dialog_title="Select Destination Folder for Shortcuts")
                if shortcut_dir:
                    existing = len([f for f in os.listdir(state.BASE_PATH) if os.path.isdir(os.path.join(state.BASE_PATH, f))])
                    for i in range(count):
                        p_name = f"Profile {existing + i + 1}"
                        p_path = os.path.join(state.BASE_PATH, p_name)
                        os.makedirs(p_path, exist_ok=True)
                        import subprocess
                        if sys.platform == "win32":
                            vbs_path = os.path.join(state.BASE_PATH, "temp.vbs")
                            lnk_path = os.path.normpath(os.path.join(shortcut_dir, f"{p_name}.lnk"))
                            vbs_code = f'Set oWS = WScript.CreateObject("WScript.Shell")\nSet oLink = oWS.CreateShortcut("{lnk_path}")\noLink.TargetPath = "{os.path.normpath(chrome_exe.value)}"\noLink.Arguments = "--user-data-dir=" & Chr(34) & "{os.path.normpath(p_path)}" & Chr(34)\noLink.Save'
                            with open(vbs_path, "w") as f:
                                f.write(vbs_code)
                            subprocess.run(["cscript", "//nologo", vbs_path], shell=True)
                            os.remove(vbs_path)
                        get_or_create_fingerprint(p_name, state.BASE_PATH)
                    refresh_profiles()
                    show_alert("Success", f"Provisioned {count} Profiles and Shortcuts.", "success")

            except Exception as err: show_alert("Error", str(err), "error")

        create_dlg = ft.AlertDialog(title=ft.Text("Create Profiles"), content=ft.Column([count_input, chrome_exe], tight=True), actions=[modern_btn("Create", on_click=on_submit)])
        show_dialog(create_dlg)

    def bulk_delete_profiles(e):
        selected = get_selected_profiles()
        if not selected: return
        def execute_delete(e):
            hide_dialog(del_dlg)
            for p_name in selected: force_delete_dir(os.path.join(state.BASE_PATH, p_name))
            refresh_profiles()
            show_alert("Deleted", "Profiles removed securely from disk.", "success")
        del_dlg = ft.AlertDialog(title=ft.Row([ft.Icon(ft.Icons.WARNING, color=C_DANGER), ft.Text("Confirm Termination", color=C_DANGER)]), content=ft.Text(f"Forcibly terminate {len(selected)} selected profiles permanently?"), actions=[modern_btn("Cancel", bgcolor="#E2E8F0", text_color=C_TEXT_DARK, on_click=lambda e: hide_dialog(del_dlg)), modern_btn("Yes, Terminate", bgcolor=C_DANGER, on_click=execute_delete)])
        show_dialog(del_dlg)

    def export_profiles(e):
        selected = get_selected_profiles()
        if not selected: return
        dest_dir = folder_fp.get_directory_path(dialog_title="Select Destination to Export Profiles")
        if dest_dir:
            import shutil
            total = len(selected)
            for i, p_name in enumerate(selected):
                src_path = os.path.join(state.BASE_PATH, p_name)
                dst_path = os.path.join(dest_dir, p_name)
                try:
                    if os.path.exists(dst_path): shutil.rmtree(dst_path)
                    shutil.copytree(src_path, dst_path)
                except Exception as err:
                    print(f"Error exporting {p_name}: {err}")
            play_success_sound()
            show_alert("Export Complete", f"Successfully exported {total} profiles to {dest_dir}", "success")

    def import_profiles(e):
        src_dir = folder_fp.get_directory_path(dialog_title="Select Folder Containing Profiles to Import")
        if src_dir:
            import shutil
            profiles_to_import = [f for f in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, f)) and f.startswith("Profile")]
            if not profiles_to_import:
                show_alert("No Profiles Found", "The selected folder does not contain any valid 'Profile X' folders.", "error")
                return
            total = len(profiles_to_import)
            for i, p_name in enumerate(profiles_to_import):
                src_path = os.path.join(src_dir, p_name)
                dst_path = os.path.join(state.BASE_PATH, p_name)
                try:
                    if not os.path.exists(dst_path): shutil.copytree(src_path, dst_path)
                except Exception as err:
                    print(f"Error importing {p_name}: {err}")
            refresh_profiles()
            play_success_sound()
            show_alert("Import Complete", f"Successfully imported {total} profiles.", "success")

    sidebar = ft.Container(
        width=260, bgcolor=C_SIDEBAR, border=border_right_only, padding=ft.Padding(left=15, top=25, right=15, bottom=20),
        content=ft.Column([
            ft.Row([ft.Container(content=ft.Icon(ft.Icons.ROCKET_LAUNCH, color=ft.Colors.WHITE, size=20), bgcolor=C_PRIMARY, padding=8, border_radius=8), ft.Text("ABIZ GLOBAL", weight=ft.FontWeight.W_900, size=18, color=C_TEXT_DARK)]),
            ft.Container(height=30),
            ft.Text("AUTOMATION", color=C_TEXT_MUTED, weight=ft.FontWeight.BOLD, size=11),
            sidebar_item("Manual Launch", ft.Icons.PLAY_ARROW, on_click=prepare_manual_queued),
            sidebar_item("Multi-Login", ft.Icons.VPN_KEY, on_click=prepare_login_queued),
            sidebar_item("Listing Engine", ft.Icons.SHOPPING_BAG, active=True, on_click=lambda e: show_dialog(config_dialog)),
            sidebar_item("Publish Drafts", ft.Icons.PUBLISH, on_click=prepare_publish_drafts),
            sidebar_item("Messenger Hub", ft.Icons.CHAT_BUBBLE_OUTLINE, on_click=lambda e: switch_main_tab(e, 1)),
            sidebar_item("Human Activity", ft.Icons.PERSON_OUTLINE, on_click=prepare_human_activity_queued),

            ft.Container(height=10),
            ft.Switch(label="Invisible Mode", value=state.HEADLESS_MODE, on_change=lambda e: setattr(state, "HEADLESS_MODE", e.control.value)),
            ft.Switch(label="Block Images", value=state.DISABLE_IMAGES, on_change=lambda e: setattr(state, "DISABLE_IMAGES", e.control.value)),

            ft.Container(height=20),
            ft.Text("MANAGEMENT", color=C_TEXT_MUTED, weight=ft.FontWeight.BOLD, size=11),
            sidebar_item("Create Profiles", ft.Icons.ADD_BOX, on_click=bulk_create_profiles),
            sidebar_item("Health Check", ft.Icons.HEALTH_AND_SAFETY, on_click=bulk_health_check),
            sidebar_item("Clean Cache", ft.Icons.CLEANING_SERVICES, on_click=lambda e: [smart_cleanup(p, state.BASE_PATH) for p in get_selected_profiles()] and show_alert("Cleaned", "Cache cleared.", "success")),
            sidebar_item("Delete Profiles", ft.Icons.DELETE, on_click=bulk_delete_profiles),
            sidebar_item("Export Profiles", ft.Icons.FILE_UPLOAD, on_click=export_profiles),
            sidebar_item("Import Profiles", ft.Icons.FILE_DOWNLOAD, on_click=import_profiles),
        ], spacing=5, scroll=ft.ScrollMode.AUTO)
    )

    # ==========================================
    # 6. MAIN DASHBOARD TAB
    # ==========================================
    profile_list = ft.ListView(height=400, spacing=0)

    def refresh_profiles(e=None):
        profile_list.controls.clear()
        app_state["profile_vars"].clear()

        folders = [f for f in os.listdir(state.BASE_PATH) if os.path.isdir(os.path.join(state.BASE_PATH, f))]
        folders.sort(key=lambda x: int(x.replace('Profile ', '')) if 'Profile ' in x else 0)

        for p in folders:
            var = ft.Checkbox(value=False)
            app_state["profile_vars"][p] = var
            logged_in = check_login_status(p, state.BASE_PATH)
            cached_status = state.app_config.get(f"status_{p}", "⚪ Logged Out" if not logged_in else "🟢 Ready")
            color = C_ACCENT if "Ready" in cached_status else C_DANGER if "Disabled" in cached_status else C_WARNING if "Checkpoint" in cached_status else C_TEXT_MUTED

            row = ft.Container(
                content=ft.Row([
                    ft.Row([var, ft.Text(p, weight=ft.FontWeight.BOLD, color=C_TEXT_DARK, width=120), ft.Container(content=ft.Row([ft.Icon(ft.Icons.CIRCLE, color=color, size=10), ft.Text(cached_status, color=color, size=12, weight=ft.FontWeight.BOLD)], spacing=4), bgcolor=ft.Colors.with_opacity(0.1, color), padding=ft.Padding(left=8, top=4, right=8, bottom=4), border_radius=12, width=120)]),
                    ft.Row([
                        icon_btn(ft.Icons.PLAY_ARROW, C_ACCENT, "Launch", on_click=lambda e, pn=p: threading.Thread(target=worker_task, args=(pn, "manual", {"url": "https://web.facebook.com"}), daemon=True).start()),
                        icon_btn(ft.Icons.VPN_KEY, C_PRIMARY, "Login", on_click=lambda e, pn=p: show_input_dialog(pn)),
                        icon_btn(ft.Icons.CHAT, "#805AD5", "Open Msgs", on_click=lambda e, pn=p: threading.Thread(target=worker_task, args=(pn, "messenger", None), daemon=True).start()),
                        icon_btn(ft.Icons.CLEANING_SERVICES, C_TEXT_MUTED, "Clean Cache", on_click=lambda e, pn=p: smart_cleanup(pn, state.BASE_PATH) or show_alert("Cleaned", f"Cache cleared for {pn}.", "success")),
                    ], spacing=10)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                bgcolor=ft.Colors.WHITE, padding=ft.Padding(left=15, top=10, right=15, bottom=10), border_radius=8, border=border_1px, margin=ft.Margin(left=0, top=0, right=0, bottom=8)
            )
            profile_list.controls.append(row)
        page.update()

    def show_input_dialog(pn):
        creds_input = ft.TextField(label=f"Enter credentials for {pn} (email,password)")
        def on_submit(e):
            hide_dialog(dlg)
            if creds_input.value and "," in creds_input.value:
                ids = creds_input.value.split(",")
                threading.Thread(target=worker_task, args=(pn, "login", None, ids[0], ids[1]), daemon=True).start()
        dlg = ft.AlertDialog(title=ft.Text("Credentials"), content=creds_input, actions=[modern_btn("Run", on_click=on_submit)])
        show_dialog(dlg)

    def select_all(e):
        for var in app_state["profile_vars"].values(): var.value = True
        page.update()

    def deselect_all(e):
        for var in app_state["profile_vars"].values(): var.value = False
        page.update()

    lbl_cpu = ft.Text("CPU: --%", color=C_TEXT_MUTED, size=12)
    lbl_ram = ft.Text("RAM: --", color=C_TEXT_MUTED, size=12)

    def monitor_resources():
        while True:
            try:
                lbl_cpu.value = f"CPU: {psutil.cpu_percent()}%"
                lbl_ram.value = f"RAM: {psutil.virtual_memory().percent}%"
                page.update()
            except: pass
            time.sleep(2)
    threading.Thread(target=monitor_resources, daemon=True).start()

    dashboard_tab = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(content=ft.Row([ft.Container(content=ft.Icon(ft.Icons.MEMORY, color=C_PRIMARY, size=28), padding=10, bgcolor="#EBF8FF", border_radius=8), ft.Column([ft.Text("System Resources", weight=ft.FontWeight.BOLD, color=C_TEXT_DARK), ft.Row([lbl_cpu, ft.Text("•", color=C_TEXT_MUTED, size=12), lbl_ram])], spacing=2)]), bgcolor=ft.Colors.WHITE, padding=15, border_radius=10, border=border_1px, expand=1),
                ft.Container(content=ft.Row([modern_btn("Stop All", icon=ft.Icons.STOP, bgcolor=C_DANGER, expand=True, on_click=emergency_stop), modern_btn("Run Master Queue", icon=ft.Icons.ROCKET_LAUNCH, bgcolor=C_PRIMARY, expand=True, on_click=run_queue_btn_click), icon_btn(ft.Icons.DELETE_SWEEP, C_TEXT_MUTED, "Clear Queue", on_click=lambda e: state.TASK_QUEUE.clear() or update_queue_display()), icon_btn(ft.Icons.CALENDAR_MONTH, C_TEXT_DARK, "Schedule", on_click=lambda e: show_dialog(scheduler_dialog))], spacing=10), bgcolor=ft.Colors.WHITE, padding=15, border_radius=10, border=border_1px, expand=2)
            ], spacing=20),
            ft.Container(content=ft.Column([lbl_global_status, progress_bar]), padding=ft.Padding(0, 10, 0, 10)),
            ft.Container(content=ft.Column([ft.Row([ft.Row([ft.Text("Profile Directory", weight=ft.FontWeight.BOLD, size=16, color=C_TEXT_DARK), lbl_qcount]), ft.Row([modern_btn("Select All", bgcolor="#EDF2F7", text_color=C_TEXT_DARK, height=30, on_click=select_all), modern_btn("Clear", bgcolor="#FFF5F5", text_color=C_DANGER, height=30, on_click=deselect_all), icon_btn(ft.Icons.REFRESH, C_PRIMARY, "Refresh", on_click=refresh_profiles)])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=10), profile_list]), expand=True)
        ]), padding=ft.Padding(left=30, top=0, right=30, bottom=30), expand=True
    )

    # ==========================================
    # 7. MESSENGER HUB TAB
    # ==========================================
    chat_header_title = ft.Text("Select a Profile", weight=ft.FontWeight.BOLD, color=C_TEXT_DARK)
    msg_sidebar_column = ft.Column([], spacing=0)
    chat_msgs_col = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True)
    active_profile = [None]

    def chat_bubble(text, is_sender=False):
        return ft.Row([ft.Container(content=ft.Text(text, color=ft.Colors.WHITE if is_sender else C_TEXT_DARK, size=13), bgcolor=C_PRIMARY if is_sender else "#EDF2F7", padding=ft.Padding(left=15, top=10, right=15, bottom=10), border_radius=ft.BorderRadius.only(top_left=12, top_right=12, bottom_left=0 if not is_sender else 12, bottom_right=0 if is_sender else 12))], alignment=ft.MainAxisAlignment.END if is_sender else ft.MainAxisAlignment.START)

    def handle_msg_select(e):
        clicked_profile = e.control.data
        active_profile[0] = clicked_profile
        chat_header_title.value = f"Inbox: {clicked_profile}"
        chat_msgs_col.controls.clear()

        chats = [c for c in getattr(state, "PENDING_MESSAGES", []) if c["profile"] == clicked_profile]
        if not chats:
            chat_msgs_col.controls.append(ft.Text("No pending messages for this profile.", color=C_TEXT_MUTED))
        else:
            for chat in chats:
                chat_msgs_col.controls.append(ft.Text(f"💬 {chat['target']}", weight=ft.FontWeight.BOLD))
                for m in chat.get("messages", []):
                    chat_msgs_col.controls.append(chat_bubble(m, False))
                # Add Reply Box
                reply_input = ft.TextField(hint_text=f"Reply to {chat['target']}...", height=40, text_size=13, border_radius=20, expand=True)
                def send_reply(e, c=chat, i=reply_input):
                    if i.value:
                        state.TASK_QUEUE.append((c["profile"], "messenger_reply", {"url": c["url"], "reply_text": i.value}, None, None))
                        update_queue_display()
                        show_alert("Reply Queued", f"Reply to {c['target']} queued.", "success")
                        i.value = ""

                        # Remove from pending dynamically
                        if c in getattr(state, "PENDING_MESSAGES", []):
                            state.PENDING_MESSAGES.remove(c)
                        refresh_messenger_sidebar()
                        handle_msg_select(ft.ControlEvent(target="", name="", data=c["profile"], control=e.control, page=page))

                chat_msgs_col.controls.append(ft.Row([reply_input, ft.Container(content=ft.Icon(ft.Icons.SEND, color=ft.Colors.WHITE, size=18), bgcolor=C_PRIMARY, padding=10, border_radius=20, ink=True, on_click=send_reply)], spacing=10))
                chat_msgs_col.controls.append(ft.Divider())
        page.update()

    def refresh_messenger_sidebar():
        msg_sidebar_column.controls.clear()
        pending = getattr(state, "PENDING_MESSAGES", [])
        profiles_with_msgs = {}
        for chat in pending:
            p = chat["profile"]
            profiles_with_msgs[p] = profiles_with_msgs.get(p, 0) + 1

        for p, count in profiles_with_msgs.items():
            active = (p == active_profile[0])
            item = ft.Container(content=ft.Row([ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=C_PRIMARY if active else C_TEXT_MUTED, size=30), ft.Text(p, weight=ft.FontWeight.BOLD, color=C_PRIMARY if active else C_TEXT_DARK)]), ft.Container(content=ft.Text(str(count), color=ft.Colors.WHITE, size=10, weight=ft.FontWeight.BOLD), bgcolor=C_DANGER, padding=ft.Padding(left=6, top=2, right=6, bottom=2), border_radius=10)]), bgcolor="#EBF8FF" if active else ft.Colors.TRANSPARENT, padding=ft.Padding(left=15, top=15, right=15, bottom=15), border=border_bottom_only, ink=True, data=p, on_click=handle_msg_select)
            msg_sidebar_column.controls.append(item)
        page.update()

    messenger_sidebar = ft.Container(width=280, bgcolor=ft.Colors.WHITE, border=border_right_only, content=ft.Column([ft.Container(content=ft.Row([ft.Text("Inbox Profiles", weight=ft.FontWeight.BOLD, size=16, color=C_TEXT_DARK), icon_btn(ft.Icons.REFRESH, C_PRIMARY, "Refresh", on_click=lambda e: refresh_messenger_sidebar())], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=ft.Padding(left=15, top=20, right=15, bottom=10), border=border_bottom_only), msg_sidebar_column], scroll=ft.ScrollMode.AUTO))
    chat_area = ft.Container(expand=True, bgcolor="#F8FAFC", content=ft.Column([ft.Container(content=ft.Row([ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=C_PRIMARY, size=40), chat_header_title])]), padding=20, bgcolor=ft.Colors.WHITE, border=border_bottom_only), ft.Container(expand=True, padding=20, content=chat_msgs_col)], spacing=0))
    messenger_tab = ft.Container(content=ft.Row([messenger_sidebar, chat_area], expand=True, spacing=0), padding=ft.Padding(left=30, top=0, right=30, bottom=30), expand=True)

    # Live polling for new messages to update sidebar
    def check_new_msgs_loop():
        while True:
            if state.NEW_MESSAGES_EVENT:
                play_success_sound()
                refresh_messenger_sidebar()
                state.NEW_MESSAGES_EVENT = False
            time.sleep(2)
    threading.Thread(target=check_new_msgs_loop, daemon=True).start()

    # ==========================================
    # 8. MAIN LAYOUT ASSEMBLY
    # ==========================================
    header = ft.Container(content=ft.Row([ft.Column([ft.Text("Enterprise Control Panel", weight=ft.FontWeight.W_900, size=24, color=C_TEXT_DARK), ft.Text("Manage your automation workflows efficiently with Abiz Global.", color=C_TEXT_MUTED, size=14)], spacing=2)]), padding=ft.Padding(left=30, top=30, right=30, bottom=20))
    main_content_area = ft.Container(content=dashboard_tab, expand=True)

    def switch_main_tab(e, index):
        main_content_area.content = [dashboard_tab, messenger_tab][index]
        for i, btn in enumerate(main_tab_row.controls):
            btn.bgcolor = "#EBF8FF" if i == index else ft.Colors.TRANSPARENT
        if index == 1: refresh_messenger_sidebar()
        page.update()

    main_tab_row = ft.Row([ft.Container(content=ft.Text("Dashboard", weight=ft.FontWeight.BOLD, color=C_PRIMARY), padding=ft.Padding(left=20, top=10, right=20, bottom=10), bgcolor="#EBF8FF", border_radius=6, ink=True, on_click=lambda e: switch_main_tab(e, 0)), ft.Container(content=ft.Text("Messenger Hub", weight=ft.FontWeight.BOLD, color=C_PRIMARY), padding=ft.Padding(left=20, top=10, right=20, bottom=10), bgcolor=ft.Colors.TRANSPARENT, border_radius=6, ink=True, on_click=lambda e: switch_main_tab(e, 1))], spacing=5)
    right_side = ft.Column([header, ft.Container(content=main_tab_row, padding=ft.Padding(left=30, top=0, right=30, bottom=10)), main_content_area], expand=True, spacing=0)
    body = ft.Row([sidebar, right_side], expand=True, spacing=0)

    # Initialize Base Path & Build UI
    def on_init_picker_result(e):
        if e.path:
            state.BASE_PATH = e.path
            state.app_config["profiles_dir"] = e.path
            state.save_config(state.app_config)
            hide_dialog(first_run_dialog)
            page.add(body)
            refresh_profiles()
        else:
            page.window.destroy()

    picker = ft.FilePicker(on_result=on_init_picker_result)
    page.overlay.append(picker)

    if not state.BASE_PATH or not os.path.exists(state.BASE_PATH):
        def open_picker_and_set(e):
            picker.get_directory_path(dialog_title="Select Master Folder")

        first_run_dialog = ft.AlertDialog(title=ft.Text("First Run Setup"), content=ft.Text("Please select a Master Folder where all browser profiles will be stored."), actions=[ft.TextButton("Select Folder", on_click=open_picker_and_set)])
        show_dialog(first_run_dialog)
    else:
        page.add(body)
        refresh_profiles()

if __name__ == "__main__":
    ft.run(main)
