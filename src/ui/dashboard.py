import os
import sys
import json
import subprocess
import threading
from tkinter import Tk, filedialog, Label, Entry, StringVar, ttk, Toplevel, simpledialog, Canvas, Frame, Scrollbar, Checkbutton, BooleanVar, Radiobutton, LEFT, RIGHT, Y, BOTH, X, BOTTOM, TOP
from PIL import Image, ImageTk

import src.state as state
from src.utils.system_utils import check_login_status, smart_cleanup, get_or_create_fingerprint, force_delete_dir, play_success_sound, force_kill_browser
from src.ui.components import HoverButton, show_alert, execute_queue_automated
import psutil
from src.automation.worker import worker_task

class ControlPanel:
    def __init__(self):
        self.root = Tk()
        self.root.title("Abiz Global - Enterprise Industrial Dashboard")
        self.root.geometry("1050x750")
        self.root.configure(bg=state.BG_APP)
        self.profile_vars = {}

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", font=("Segoe UI", 10), padding=6, relief="flat", background=state.BG_PANEL)
        style.configure("TProgressbar", thickness=10, background=state.BTN_GREEN)
        style.configure("TNotebook", background=state.BG_APP, borderwidth=0)
        style.configure("TNotebook.Tab", background="#E2E8F0", foreground=state.FG_TEXT, padding=10, font=("Segoe UI", 9))
        style.map("TNotebook.Tab", background=[("selected", state.BG_PANEL)], foreground=[("selected", state.BTN_BLUE)])

        header = Frame(self.root, bg=state.BG_PANEL, height=80, bd=1, relief="solid", highlightbackground=state.BORDER_COLOR, highlightthickness=1)
        header.pack(fill=X, side=TOP)
        Label(header, text="ABIZ GLOBAL ENTERPRISE", font=("Segoe UI", 22, "bold"), fg=state.BTN_BLUE, bg=state.BG_PANEL).pack(pady=15)

        main_layout = Frame(self.root, bg=state.BG_APP)
        main_layout.pack(fill=BOTH, expand=True, padx=25, pady=(15,0))

        # --- LEFT PANE ---
        left_pane = Frame(main_layout, bg=state.BG_APP, width=320)
        left_pane.pack(side=LEFT, fill=Y, padx=(0, 20))

        bulk_auto_frame = Frame(left_pane, bg=state.BG_PANEL, bd=1, relief="solid", highlightbackground=state.BORDER_COLOR, highlightthickness=1)
        bulk_auto_frame.pack(fill=X, pady=(0, 20))
        Label(bulk_auto_frame, text="⚙️ AUTOMATION (MULTI)", font=("Segoe UI", 12, "bold"), fg=state.FG_TEXT, bg=state.BG_PANEL).pack(pady=(15,10))

        HoverButton(bulk_auto_frame, text="▶ Queued Manual Launch", hover_color=state.BTN_GREEN_HOVER, command=self.prepare_manual_queued, bg=state.BTN_GREEN, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=6)
        HoverButton(bulk_auto_frame, text="🔑 Queued Multi-Login", hover_color=state.BTN_BLUE_HOVER, command=self.prepare_login_queued, bg=state.BTN_BLUE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=6)
        HoverButton(bulk_auto_frame, text="🛍️ Queued Multi-Listing", hover_color=state.BTN_ORANGE_HOVER, command=self.open_multi_listing_form, bg=state.BTN_ORANGE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=6)
        HoverButton(bulk_auto_frame, text="💬 Queued Messenger Inbox", hover_color=state.BTN_PURPLE_HOVER, command=self.prepare_messenger_queued, bg=state.BTN_PURPLE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=6)

        HoverButton(bulk_auto_frame, text="📬 LIVE MESSAGES HUB", hover_color="#4F46E5", command=self.open_messenger_hub, bg="#4338CA", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=(6,0))
        Label(bulk_auto_frame, text="", bg=state.BG_PANEL).pack()

        mgt_frame = Frame(left_pane, bg=state.BG_PANEL, bd=1, relief="solid", highlightbackground=state.BORDER_COLOR, highlightthickness=1)
        mgt_frame.pack(fill=X)
        Label(mgt_frame, text="📂 PROFILE MANAGEMENT", font=("Segoe UI", 12, "bold"), fg=state.FG_TEXT, bg=state.BG_PANEL).pack(pady=(15,10))
        HoverButton(mgt_frame, text="➕ Create Profiles & Shortcuts", hover_color="#475569", command=self.bulk_create, bg="#64748B", fg="white", font=("Segoe UI", 10), relief="flat", cursor="hand2").pack(fill=X, padx=20, pady=5)
        HoverButton(mgt_frame, text="🧹 Clean Cache & Temp Data", hover_color="#6B7280", command=self.bulk_clear_cache, bg="#9CA3AF", fg="white", font=("Segoe UI", 10), relief="flat", cursor="hand2").pack(fill=X, padx=20, pady=5)
        HoverButton(mgt_frame, text="🗑️ Delete Profiles (Immediate)", hover_color=state.BTN_RED_HOVER, command=self.bulk_delete_immediate, bg=state.BTN_RED, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2").pack(fill=X, padx=20, pady=5)

        HoverButton(mgt_frame, text="📦 Export Profiles", hover_color="#10B981", command=self.export_profiles, bg="#059669", fg="white", font=("Segoe UI", 10), relief="flat", cursor="hand2").pack(fill=X, padx=20, pady=5)
        HoverButton(mgt_frame, text="📥 Import Profiles", hover_color="#3B82F6", command=self.import_profiles, bg="#2563EB", fg="white", font=("Segoe UI", 10), relief="flat", cursor="hand2").pack(fill=X, padx=20, pady=5)

        Label(mgt_frame, text="", bg=state.BG_PANEL).pack()

        # --- RIGHT PANE ---
        right_pane = Frame(main_layout, bg=state.BG_APP)
        right_pane.pack(side=RIGHT, fill=BOTH, expand=True)

        # Create Notebook for Main Tabs
        self.notebook = ttk.Notebook(right_pane)
        self.notebook.pack(fill=BOTH, expand=True)

        self.tab_dashboard = Frame(self.notebook, bg=state.BG_APP)
        self.notebook.add(self.tab_dashboard, text=" Dashboard ")

        self.tab_messenger = Frame(self.notebook, bg=state.BG_APP)
        self.notebook.add(self.tab_messenger, text=" Messenger Hub ")

        scanner_frame = Frame(self.tab_dashboard, bg=state.BG_PANEL, bd=1, relief="solid", highlightbackground=state.BORDER_COLOR, highlightthickness=1)
        scanner_frame.pack(fill=BOTH, expand=True, pady=(0, 15))

        stf = Frame(scanner_frame, bg=state.BG_PANEL)
        stf.pack(fill=X, pady=10, padx=15)
        Label(stf, text="📋 PROFILE DIRECTORY (SCANNER)", font=("Segoe UI", 13, "bold"), fg=state.FG_TEXT, bg=state.BG_PANEL).pack(side=LEFT)
        HoverButton(stf, text="🔄 Refresh", hover_color="#CBD5E1", command=self.refresh_profiles, bg="#E2E8F0", fg=state.FG_TEXT, font=("Segoe UI", 9, "bold"), relief="flat", padx=10, cursor="hand2").pack(side=RIGHT, padx=(5,0))
        HoverButton(stf, text="Select All", hover_color="#CBD5E1", command=self.select_all, bg="#E2E8F0", fg=state.FG_TEXT, font=("Segoe UI", 9, "bold"), relief="flat", padx=10, cursor="hand2").pack(side=RIGHT)
        HoverButton(stf, text="Deselect All", hover_color="#FEE2E2", command=self.deselect_all, bg="#FEF2F2", fg=state.BTN_RED, font=("Segoe UI", 9, "bold"), relief="flat", padx=10, cursor="hand2").pack(side=RIGHT, padx=5)

        canvas_frame = Frame(scanner_frame, bg=state.BG_PANEL)
        canvas_frame.pack(fill=BOTH, expand=True, padx=15, pady=(0, 15))
        self.canvas = Canvas(canvas_frame, bg=state.BG_PANEL, highlightthickness=0)
        scrollbar = Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = Frame(self.canvas, bg=state.BG_PANEL)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel binding (cross-platform handling including touchpads)
        def _on_mousewheel(event):
            if hasattr(event, "delta") and event.delta:
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif hasattr(event, "num"):
                if event.num == 4:
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(1, "units")

        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.canvas.bind("<Button-4>", _on_mousewheel)
        self.canvas.bind("<Button-5>", _on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-4>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-5>", _on_mousewheel)

        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # System Resource Monitor
        self.sys_frame = Frame(self.tab_dashboard, bg=state.BG_PANEL, bd=1, relief="solid", highlightbackground=state.BORDER_COLOR, highlightthickness=1)
        self.sys_frame.pack(fill=X, pady=(0, 15))
        sys_inner = Frame(self.sys_frame, bg=state.BG_PANEL)
        sys_inner.pack(fill=X, padx=15, pady=10)
        Label(sys_inner, text="🖥️ SYSTEM RESOURCES:", font=("Segoe UI", 12, "bold"), fg=state.FG_TEXT, bg=state.BG_PANEL).pack(side=LEFT)
        self.lbl_cpu = Label(sys_inner, text="CPU: 0%", font=("Segoe UI", 10, "bold"), fg=state.BTN_BLUE, bg=state.BG_PANEL)
        self.lbl_cpu.pack(side=LEFT, padx=(20, 10))
        self.lbl_ram = Label(sys_inner, text="RAM: 0%", font=("Segoe UI", 10, "bold"), fg=state.BTN_PURPLE, bg=state.BG_PANEL)
        self.lbl_ram.pack(side=LEFT, padx=10)

        queue_frame = Frame(self.tab_dashboard, bg=state.BG_PANEL, bd=1, relief="solid", highlightbackground=state.BORDER_COLOR, highlightthickness=1)
        queue_frame.pack(fill=X)
        qtf = Frame(queue_frame, bg=state.BG_PANEL)
        qtf.pack(fill=X, padx=15, pady=5)
        Label(qtf, text="⚙️ TASK QUEUE (PENDING)", font=("Segoe UI", 12, "bold"), fg=state.FG_TEXT, bg=state.BG_PANEL).pack(side=LEFT)
        self.lbl_qcount = Label(qtf, text="0 tasks queued", font=("Segoe UI", 9), fg="#64748B", bg=state.BG_PANEL)
        self.lbl_qcount.pack(side=RIGHT)

        qbf = Frame(queue_frame, bg=state.BG_PANEL)
        qbf.pack(fill=X, padx=15, pady=10)
        HoverButton(qbf, text="🗑️ Clear Queue", hover_color="#475569", command=self.clear_queue_list, bg="#64748B", fg="white", font=("Segoe UI", 10), relief="flat", width=15).pack(side=LEFT, padx=(0,5))
        HoverButton(qbf, text="🛑 STOP ALL", hover_color=state.BTN_RED_HOVER, command=self.emergency_stop, bg=state.BTN_RED, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", width=15).pack(side=LEFT, padx=5)
        HoverButton(qbf, text="🚀 RUN MASTER QUEUE", hover_color=state.BTN_GREEN_HOVER, command=self.run_master_queue_automated, bg=state.BTN_GREEN, fg="white", font=("Segoe UI", 10, "bold"), relief="flat").pack(side=RIGHT, fill=X, expand=True, padx=(5,0))

        bottom_frame = Frame(self.root, bg=state.BG_APP)
        bottom_frame.pack(fill=X, side=BOTTOM, pady=10)
        self.progress = ttk.Progressbar(bottom_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill=X, padx=25)

        if not os.path.exists(state.BASE_PATH):
            os.makedirs(state.BASE_PATH)

        self.build_messenger_tab()

        self.refresh_profiles()
        self.update_queue_display()
        self.update_system_resources()
        self.check_new_messages()

    def export_profiles(self):
        selected = self.get_selected_profiles()
        if not selected: return

        dest_dir = filedialog.askdirectory(title="Select Destination to Export Profiles", parent=self.root)
        if not dest_dir: return

        import shutil
        total = len(selected)
        self.progress.config(value=0)

        for i, p_name in enumerate(selected):
            src_path = os.path.join(state.BASE_PATH, p_name)
            dst_path = os.path.join(dest_dir, p_name)
            try:
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
            except Exception as e:
                print(f"Error exporting {p_name}: {e}")
            self.progress.config(value=((i+1)/total)*100)

        self.progress.config(value=0)
        play_success_sound()
        show_alert(self.root, "Export Complete", f"Successfully exported {total} profiles to {dest_dir}", "success")

    def import_profiles(self):
        src_dir = filedialog.askdirectory(title="Select Folder Containing Profiles to Import", parent=self.root)
        if not src_dir: return

        import shutil
        profiles_to_import = [f for f in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, f)) and f.startswith("Profile")]

        if not profiles_to_import:
            show_alert(self.root, "No Profiles Found", "The selected folder does not contain any valid 'Profile X' folders.", "error")
            return

        total = len(profiles_to_import)
        self.progress.config(value=0)

        for i, p_name in enumerate(profiles_to_import):
            src_path = os.path.join(src_dir, p_name)
            dst_path = os.path.join(state.BASE_PATH, p_name)
            try:
                if not os.path.exists(dst_path):
                    shutil.copytree(src_path, dst_path)
            except Exception as e:
                print(f"Error importing {p_name}: {e}")
            self.progress.config(value=((i+1)/total)*100)

        self.refresh_profiles()
        self.progress.config(value=0)
        play_success_sound()
        show_alert(self.root, "Import Complete", f"Successfully imported {total} profiles.", "success")

    def check_new_messages(self):
        if state.NEW_MESSAGES_EVENT:
            play_success_sound()
            self.refresh_messenger_hub()
            state.NEW_MESSAGES_EVENT = False
        self.root.after(2000, self.check_new_messages)

    def build_messenger_tab(self):
        # Left Panel for Profiles
        self.msg_left_pane = Frame(self.tab_messenger, bg=state.BG_PANEL, bd=1, relief="solid", highlightbackground=state.BORDER_COLOR, highlightthickness=1, width=250)
        self.msg_left_pane.pack(side=LEFT, fill=Y, padx=(0, 15), pady=15)
        self.msg_left_pane.pack_propagate(False)

        Label(self.msg_left_pane, text="📬 INBOX PROFILES", font=("Segoe UI", 12, "bold"), fg=state.FG_TEXT, bg=state.BG_PANEL).pack(pady=15)

        self.msg_profiles_canvas = Canvas(self.msg_left_pane, bg=state.BG_PANEL, highlightthickness=0)
        self.msg_profiles_scrollbar = Scrollbar(self.msg_left_pane, orient="vertical", command=self.msg_profiles_canvas.yview)
        self.msg_profiles_inner = Frame(self.msg_profiles_canvas, bg=state.BG_PANEL)

        self.msg_profiles_inner.bind("<Configure>", lambda e: self.msg_profiles_canvas.configure(scrollregion=self.msg_profiles_canvas.bbox("all")))
        self.msg_profiles_canvas.create_window((0, 0), window=self.msg_profiles_inner, anchor="nw")
        self.msg_profiles_canvas.configure(yscrollcommand=self.msg_profiles_scrollbar.set)

        def _on_mousewheel_msg_profiles(event):
            if hasattr(event, "delta") and event.delta:
                self.msg_profiles_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif hasattr(event, "num"):
                if event.num == 4:
                    self.msg_profiles_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.msg_profiles_canvas.yview_scroll(1, "units")

        self.msg_profiles_canvas.bind("<MouseWheel>", _on_mousewheel_msg_profiles)
        self.msg_profiles_canvas.bind("<Button-4>", _on_mousewheel_msg_profiles)
        self.msg_profiles_canvas.bind("<Button-5>", _on_mousewheel_msg_profiles)
        self.msg_profiles_inner.bind("<MouseWheel>", _on_mousewheel_msg_profiles)
        self.msg_profiles_inner.bind("<Button-4>", _on_mousewheel_msg_profiles)
        self.msg_profiles_inner.bind("<Button-5>", _on_mousewheel_msg_profiles)

        self.msg_profiles_canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        self.msg_profiles_scrollbar.pack(side=RIGHT, fill=Y)

        # Right Panel for Chats
        self.msg_right_pane = Frame(self.tab_messenger, bg=state.BG_PANEL, bd=1, relief="solid", highlightbackground=state.BORDER_COLOR, highlightthickness=1)
        self.msg_right_pane.pack(side=RIGHT, fill=BOTH, expand=True, pady=15)

        self.msg_chat_title = Label(self.msg_right_pane, text="Select a profile to view unread chats", font=("Segoe UI", 14, "bold"), bg=state.BG_PANEL, fg=state.BTN_BLUE)
        self.msg_chat_title.pack(pady=15)

        self.msg_canvas = Canvas(self.msg_right_pane, bg=state.BG_PANEL, highlightthickness=0)
        self.msg_scrollbar = Scrollbar(self.msg_right_pane, orient="vertical", command=self.msg_canvas.yview)
        self.msg_inner_frame = Frame(self.msg_canvas, bg=state.BG_PANEL)

        self.msg_inner_frame.bind("<Configure>", lambda e: self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all")))
        self.msg_canvas.create_window((0, 0), window=self.msg_inner_frame, anchor="nw")
        self.msg_canvas.configure(yscrollcommand=self.msg_scrollbar.set)

        def _on_mousewheel_msg_chats(event):
            if hasattr(event, "delta") and event.delta:
                self.msg_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif hasattr(event, "num"):
                if event.num == 4:
                    self.msg_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.msg_canvas.yview_scroll(1, "units")

        self.msg_canvas.bind("<MouseWheel>", _on_mousewheel_msg_chats)
        self.msg_canvas.bind("<Button-4>", _on_mousewheel_msg_chats)
        self.msg_canvas.bind("<Button-5>", _on_mousewheel_msg_chats)
        self.msg_inner.bind("<MouseWheel>", _on_mousewheel_msg_chats)
        self.msg_inner.bind("<Button-4>", _on_mousewheel_msg_chats)
        self.msg_inner.bind("<Button-5>", _on_mousewheel_msg_chats)

        self.msg_canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)
        self.msg_scrollbar.pack(side=RIGHT, fill=Y)

        self.active_messenger_profile = None

    def refresh_messenger_hub(self):
        if not hasattr(self, 'msg_profiles_inner'): return

        # We read from state.PENDING_MESSAGES
        if not hasattr(state, "PENDING_MESSAGES"):
            state.PENDING_MESSAGES = []

        pending = state.PENDING_MESSAGES

        # Group by profile
        profiles_with_msgs = {}
        for chat in pending:
            p = chat["profile"]
            profiles_with_msgs[p] = profiles_with_msgs.get(p, 0) + 1

        # Clear left pane
        for widget in self.msg_profiles_inner.winfo_children():
            widget.destroy()

        if not profiles_with_msgs:
            Label(self.msg_profiles_inner, text="No unread chats.", fg="#94A3B8", bg=state.BG_PANEL).pack(pady=20)
        else:
            for p, count in profiles_with_msgs.items():
                btn_text = f"{p} ({count})"
                color = state.BTN_BLUE if p == self.active_messenger_profile else "#E2E8F0"
                fg_color = "white" if p == self.active_messenger_profile else state.FG_TEXT

                btn = HoverButton(self.msg_profiles_inner, text=btn_text, hover_color=state.BTN_BLUE_HOVER,
                                  command=lambda p_name=p: self.select_messenger_profile(p_name),
                                  bg=color, fg=fg_color, font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2")
                btn.pack(fill=X, pady=5, padx=5)

        # Refresh right pane
        self.select_messenger_profile(self.active_messenger_profile)

    def select_messenger_profile(self, p_name):
        self.active_messenger_profile = p_name

        for widget in self.msg_inner_frame.winfo_children():
            widget.destroy()

        if not p_name:
            self.msg_chat_title.config(text="Select a profile to view unread chats")
            return

        self.msg_chat_title.config(text=f"Inbox: {p_name}")

        chats = [c for c in getattr(state, "PENDING_MESSAGES", []) if c["profile"] == p_name]

        if not chats:
            Label(self.msg_inner_frame, text="No pending messages for this profile.", bg=state.BG_PANEL, fg="#94A3B8", font=("Segoe UI", 12)).pack(pady=50)
            # Re-render left panel to update selection color
            # We don't call refresh_messenger_hub directly to avoid recursion,
            # but setting active profile might trigger it. We just leave it.
            return

        for idx, chat in enumerate(chats):
            card = Frame(self.msg_inner_frame, bg="#F8FAFC", bd=1, relief="solid", highlightbackground=state.BORDER_COLOR, highlightthickness=1)
            card.pack(fill=X, pady=10, padx=5)

            header = Frame(card, bg="#E2E8F0")
            header.pack(fill=X)
            Label(header, text=f"💬 {chat['target']}", font=("Segoe UI", 11, "bold"), bg="#E2E8F0", fg=state.FG_TEXT).pack(side=LEFT, padx=10, pady=5)
            Label(header, text=f"({p_name})", font=("Segoe UI", 9, "italic"), bg="#E2E8F0", fg="#64748B").pack(side=RIGHT, padx=10, pady=5)

            msg_area = Frame(card, bg="#F8FAFC")
            msg_area.pack(fill=X, padx=10, pady=10)

            for m in chat.get("messages", []):
                Label(msg_area, text=m, bg="#F8FAFC", fg="#475569", font=("Segoe UI", 10), wraplength=450, justify=LEFT).pack(anchor="w")

            reply_frame = Frame(card, bg="#F8FAFC")
            reply_frame.pack(fill=X, padx=10, pady=(0,10))

            reply_entry = Entry(reply_frame, font=("Segoe UI", 10), width=40)
            reply_entry.pack(side=LEFT, fill=X, expand=True, padx=(0,10))

            HoverButton(reply_frame, text="📤 Send Reply", hover_color=state.BTN_GREEN_HOVER,
                        command=lambda c=chat, e=reply_entry: self.submit_reply(c, e),
                        bg=state.BTN_GREEN, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2").pack(side=RIGHT)

    def submit_reply(self, chat_obj, entry_widget):
        text = entry_widget.get().strip()
        if not text:
            pass

        if text:
            state.TASK_QUEUE.append((chat_obj["profile"], "messenger_reply", {"url": chat_obj["url"], "reply_text": text}, None, None))
            self.update_queue_display()
            show_alert(self.root, "Reply Queued", f"Reply to {chat_obj['target']} queued. Run Master Queue to send.", "success")

        if hasattr(state, "PENDING_MESSAGES") and chat_obj in state.PENDING_MESSAGES:
            state.PENDING_MESSAGES.remove(chat_obj)

        self.refresh_messenger_hub()

    def update_system_resources(self):
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            self.lbl_cpu.config(text=f"CPU: {cpu}%")
            self.lbl_ram.config(text=f"RAM: {ram}%")
        except:
            pass
        self.root.after(2000, self.update_system_resources)

    def update_queue_display(self):
        self.lbl_qcount.config(text=f"{len(state.TASK_QUEUE)} automated tasks queued")

    def clear_queue_list(self):
        state.TASK_QUEUE.clear()
        self.update_queue_display()

    def emergency_stop(self):
        state.GLOBAL_STOP = True
        print("\n[EMERGENCY] STOP ALL COMMAND RECEIVED. FORCIBLY TERMINATING DRIVERS...")
        for driver in state.ACTIVE_DRIVERS:
            force_kill_browser(driver)
        state.ACTIVE_DRIVERS.clear()

        # Additional aggressive global sweep for safety
        if sys.platform == "win32":
            try:
                import subprocess
                subprocess.run('taskkill /F /IM chrome.exe /T', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run('taskkill /F /IM chromedriver.exe /T', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except:
                pass

        show_alert(self.root, "Stopped", "Automation halted forcefully. Ghost processes killed.", "error")

    def refresh_profiles(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.profile_vars.clear()

        folders = [f for f in os.listdir(state.BASE_PATH) if os.path.isdir(os.path.join(state.BASE_PATH, f))]
        folders.sort(key=lambda x: int(x.replace('Profile ', '')) if 'Profile ' in x else 0)

        header_row = Frame(self.scrollable_frame, bg=state.BG_PANEL)
        header_row.pack(fill=X, pady=(0, 5))
        Label(header_row, text="", width=4, bg=state.BG_PANEL).pack(side=LEFT)
        Label(header_row, text="PROFILE NAME", font=("Segoe UI", 9, "bold"), fg="#64748B", bg=state.BG_PANEL, anchor="w", width=20).pack(side=LEFT)
        Label(header_row, text="STATUS", font=("Segoe UI", 9, "bold"), fg="#64748B", bg=state.BG_PANEL, anchor="w", width=15).pack(side=LEFT)
        Label(header_row, text="INDIVIDUAL ACTIONS", font=("Segoe UI", 9, "bold"), fg="#64748B", bg=state.BG_PANEL).pack(side=LEFT)

        for p in folders:
            var = BooleanVar()
            self.profile_vars[p] = var
            row = Frame(self.scrollable_frame, bg=state.BG_PANEL)
            row.pack(fill=X, pady=2)

            Checkbutton(row, variable=var, bg=state.BG_PANEL).pack(side=LEFT, padx=(3,0))
            Label(row, text=p, font=("Segoe UI", 10), fg=state.FG_TEXT, bg=state.BG_PANEL, anchor="w", width=18).pack(side=LEFT, padx=5)

            logged_in = check_login_status(p, state.BASE_PATH)
            status_text = "🟢  Ready" if logged_in else "⚪  Offline"
            color = state.BTN_GREEN if logged_in else "#9CA3AF"
            Label(row, text=status_text, font=("Segoe UI", 9, "bold"), fg=color, bg=state.BG_PANEL, anchor="w", width=13).pack(side=LEFT, padx=5)

            btn_frame = Frame(row, bg=state.BG_PANEL)
            btn_frame.pack(side=LEFT)
            HoverButton(btn_frame, text="⚡ Launch", hover_color=state.BTN_GREEN_HOVER, command=lambda pn=p: self.run_single_immediate(pn, "manual"), bg=state.BTN_GREEN, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=4).pack(side=LEFT, padx=2)
            HoverButton(btn_frame, text="🔑 Login", hover_color=state.BTN_BLUE_HOVER, command=lambda pn=p: self.run_single_immediate(pn, "login_auto"), bg=state.BTN_BLUE, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=4).pack(side=LEFT, padx=2)
            HoverButton(btn_frame, text="🛍️ Listing", hover_color=state.BTN_ORANGE_HOVER, command=lambda pn=p: self.open_single_listing_form(pn), bg=state.BTN_ORANGE, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=4).pack(side=LEFT, padx=2)
            HoverButton(btn_frame, text="💬 Msgs", hover_color=state.BTN_PURPLE_HOVER, command=lambda pn=p: self.run_single_immediate(pn, "messenger"), bg=state.BTN_PURPLE, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=4).pack(side=LEFT, padx=2)
            HoverButton(btn_frame, text="🧹 Clean", hover_color="#6B7280", command=lambda pn=p: self.single_clean(pn), bg="#9CA3AF", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=4).pack(side=LEFT, padx=2)
            HoverButton(btn_frame, text="🗑️ Del", hover_color=state.BTN_RED_HOVER, command=lambda pn=p: self.single_delete(pn), bg=state.BTN_RED, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=4).pack(side=LEFT, padx=2)

    def select_all(self):
        for var in self.profile_vars.values():
            var.set(True)

    def deselect_all(self):
        for var in self.profile_vars.values():
            var.set(False)

    def get_selected_profiles(self):
        selected = [p for p, var in self.profile_vars.items() if var.get()]
        if not selected:
            show_alert(self.root, "Selection Required", "Please select at least one profile via scanner checkboxes.", "error")
        return selected

    def ask_thread_count(self, num_tasks):
        if num_tasks == 1:
            return 1
        return simpledialog.askinteger("Concurrency Config", f"How many parallel threads for {num_tasks} tasks? (1-10):", minvalue=1, maxvalue=10, parent=self.root)

    def add_automated_to_queue(self, profiles, task_type, details=None):
        if task_type == "login_multi_automated":
            filepath = filedialog.askopenfilename(title="Select Accounts IDs Text File", filetypes=[("Text Files", "*.txt")], parent=self.root)
            if not filepath:
                return
            with open(filepath, "r") as f:
                ids = [line.strip().split(",") for line in f if "," in line]
            for i, p_name in enumerate(profiles):
                if i < len(ids):
                    state.TASK_QUEUE.append((p_name, "login", None, ids[i][0], ids[i][1]))
        else:
            for p in profiles:
                state.TASK_QUEUE.append((p, task_type, details, None, None))

        self.update_queue_display()
        show_alert(self.root, "Added to Queue", f"{len(profiles)} tasks added to pending automated queue.", "success")

    def single_clean(self, p_name):
        smart_cleanup(p_name, state.BASE_PATH)
        show_alert(self.root, "Cleaned", f"Cache cleared for {p_name}.", "success")

    def single_delete(self, p_name):
        if simpledialog.messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {p_name} permanently?"):
            force_delete_dir(os.path.join(state.BASE_PATH, p_name))
            self.refresh_profiles()
            play_success_sound()
            show_alert(self.root, "Deleted", f"{p_name} was removed.", "success")

    def open_messenger_hub(self):
        # We now have an embedded Messenger Hub tab, so just select it
        if hasattr(self, 'notebook'):
            self.notebook.select(self.tab_messenger)


    def open_single_listing_form(self, p_name):
        # We temporarily set the profile selection to just this one profile to reuse the multi-listing form
        for k, v in self.profile_vars.items():
            v.set(False)
        self.profile_vars[p_name].set(True)
        self.open_multi_listing_form()

    def run_single_immediate(self, p_name, task_type):
        if task_type == "manual":
            sf = Toplevel(self.root)
            sf.title("Manual Launch Configuration")
            sf.geometry("380x250")
            sf.configure(bg=state.BG_PANEL)
            Frame(sf, bg=state.BTN_GREEN, height=6).pack(fill=X, side=TOP)
            Label(sf, text="Configure Startup URL", font=("Segoe UI", 11, "bold"), bg=state.BG_PANEL, fg=state.FG_TEXT).pack(pady=15)

            target_var = StringVar(value="fb")
            Radiobutton(sf, text="Facebook Default", variable=target_var, value="fb", bg=state.BG_PANEL).pack(anchor="w", padx=40)
            Radiobutton(sf, text="Blank New Tab", variable=target_var, value="blank", bg=state.BG_PANEL).pack(anchor="w", padx=40)
            custom_frame = Frame(sf, bg=state.BG_PANEL)
            custom_frame.pack(anchor="w", padx=40, pady=5)
            Radiobutton(custom_frame, text="Custom URL:", variable=target_var, value="custom", bg=state.BG_PANEL).pack(side=LEFT)
            custom_url_entry = Entry(custom_frame, width=30)
            custom_url_entry.pack(side=LEFT)

            def launch_sf():
                t = target_var.get()
                url = "https://web.facebook.com" if t == "fb" else "about:blank" if t == "blank" else custom_url_entry.get()
                sf.destroy()
                threading.Thread(target=worker_task, args=(p_name, "manual", {"url": url}), daemon=True).start()

            HoverButton(sf, text="Launch Immediately", command=launch_sf, bg=state.BTN_GREEN, hover_color=state.BTN_GREEN_HOVER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat").pack(pady=20)
            return

        elif task_type == "login_auto":
            filepath = filedialog.askopenfilename(title=f"Select Credentials Text File for {p_name}", filetypes=[("Text Files", "*.txt")], parent=self.root)
            if not filepath:
                return
            try:
                with open(filepath, "r") as f:
                    for line in f:
                        if "," in line:
                            ids = line.strip().split(",")
                            threading.Thread(target=worker_task, args=(p_name, "login", None, ids[0], ids[1]), daemon=True).start()
                            return
                show_alert(self.root, "Invalid Format", "No valid 'email,password' format found in the text file.", "error")
            except Exception as e:
                show_alert(self.root, "Error", f"Could not read file: {e}", "error")
            return
        elif task_type == "messenger":
            threading.Thread(target=worker_task, args=(p_name, "messenger", None, None, None), daemon=True).start()
            return

    def prepare_manual_queued(self):
        selected = self.get_selected_profiles()
        if not selected:
            return

        sf = Toplevel(self.root)
        sf.title("Queued Manual Launch")
        sf.geometry("380x250")
        sf.configure(bg=state.BG_PANEL)
        Frame(sf, bg=state.BTN_GREEN, height=6).pack(fill=X, side=TOP)
        Label(sf, text="Configure Startup URL", font=("Segoe UI", 11, "bold"), bg=state.BG_PANEL, fg=state.FG_TEXT).pack(pady=15)

        target_var = StringVar(value="fb")
        Radiobutton(sf, text="Facebook Default", variable=target_var, value="fb", bg=state.BG_PANEL).pack(anchor="w", padx=40)
        Radiobutton(sf, text="Blank New Tab", variable=target_var, value="blank", bg=state.BG_PANEL).pack(anchor="w", padx=40)
        custom_frame = Frame(sf, bg=state.BG_PANEL)
        custom_frame.pack(anchor="w", padx=40, pady=5)
        Radiobutton(custom_frame, text="Custom URL:", variable=target_var, value="custom", bg=state.BG_PANEL).pack(side=LEFT)
        custom_url_entry2 = Entry(custom_frame, width=30)
        custom_url_entry2.pack(side=LEFT)

        def queue_manual_launch():
            t = target_var.get()
            url = "https://web.facebook.com" if t == "fb" else "about:blank" if t == "blank" else custom_url_entry2.get()
            sf.destroy()
            self.add_automated_to_queue(selected, "manual", {"url": url})

        HoverButton(sf, text="Add to Queue", command=queue_manual_launch, bg=state.BTN_GREEN, hover_color=state.BTN_GREEN_HOVER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat").pack(pady=20)

    def prepare_login_queued(self):
        selected = self.get_selected_profiles()
        if not selected:
            return
        self.add_automated_to_queue(selected, "login_multi_automated")

    def prepare_messenger_queued(self):
        selected = self.get_selected_profiles()
        if not selected:
            return
        self.add_automated_to_queue(selected, "messenger")

    def run_master_queue_automated(self):
        if not state.TASK_QUEUE:
            show_alert(self.root, "Queue Empty", "Add tasks to the queue first before running.", "error")
            return

        threads = self.ask_thread_count(len(state.TASK_QUEUE))
        if not threads:
            return
        threading.Thread(target=execute_queue_automated, args=(threads, self.root, self.progress, self.update_queue_display), daemon=True).start()

    def bulk_create(self):
        count = simpledialog.askinteger("Create Profiles", "How many new profiles to provision?", minvalue=1, parent=self.root)
        if not count:
            return
        chrome_exe = simpledialog.askstring("Chrome Path", "Provide path to Chrome.exe executable:", parent=self.root)
        if not chrome_exe:
            return
        shortcut_dir = filedialog.askdirectory(title="Select Destination Folder for Shortcuts", parent=self.root)
        if not shortcut_dir:
            return

        existing = len([f for f in os.listdir(state.BASE_PATH) if os.path.isdir(os.path.join(state.BASE_PATH, f))])
        for i in range(count):
            p_name = f"Profile {existing + i + 1}"
            p_path = os.path.join(state.BASE_PATH, p_name)
            os.makedirs(p_path, exist_ok=True)
            vbs_path = os.path.join(state.BASE_PATH, "temp.vbs")
            lnk_path = os.path.normpath(os.path.join(shortcut_dir, f"{p_name}.lnk"))
            vbs_code = f'Set oWS = WScript.CreateObject("WScript.Shell")\nSet oLink = oWS.CreateShortcut("{lnk_path}")\noLink.TargetPath = "{os.path.normpath(chrome_exe)}"\noLink.Arguments = "--user-data-dir=" & Chr(34) & "{os.path.normpath(p_path)}" & Chr(34)\noLink.Save'

            with open(vbs_path, "w") as f:
                f.write(vbs_code)
            subprocess.run(["cscript", "//nologo", vbs_path], shell=True)
            os.remove(vbs_path)
            get_or_create_fingerprint(p_name, state.BASE_PATH)

        self.refresh_profiles()
        play_success_sound()
        show_alert(self.root, "Success", f"Provisioned {count} Profiles and Shortcuts.", "success")

    def bulk_delete_immediate(self):
        selected = self.get_selected_profiles()
        if not selected:
            return

        alert_box = Toplevel(self.root)
        alert_box.title("Confirm Termination")
        alert_box.geometry("400x150")
        alert_box.configure(bg=state.BG_PANEL)
        alert_box.transient(self.root)
        alert_box.grab_set()

        Frame(alert_box, bg=state.BTN_RED, height=6).pack(fill=X, side=TOP)
        Label(alert_box, text="Confirm Termination", font=("Segoe UI", 12, "bold"), bg=state.BG_PANEL, fg=state.BTN_RED).pack(pady=(15, 5))
        Label(alert_box, text=f"Forcibly terminate {len(selected)} selected profiles permanently?", font=("Segoe UI", 10), bg=state.BG_PANEL, fg=state.FG_TEXT).pack(pady=5)

        def execute_delete():
            alert_box.destroy()
            print(f"\n[SYSTEM] Deleting {len(selected)} profiles securely...")
            total = len(selected)
            self.progress.config(value=0)
            for i, p_name in enumerate(selected):
                force_delete_dir(os.path.join(state.BASE_PATH, p_name))
                self.progress.config(value=((i+1)/total)*100)
            self.refresh_profiles()
            self.progress.config(value=0)
            play_success_sound()
            show_alert(self.root, "Profiles Deleted", "Profiles removed securely from disk.", "success")

        btn_frame = Frame(alert_box, bg=state.BG_PANEL)
        btn_frame.pack(pady=10)
        HoverButton(btn_frame, text="Yes, Terminate", command=execute_delete, bg=state.BTN_RED, hover_color=state.BTN_RED_HOVER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2").pack(side=LEFT, padx=10)
        HoverButton(btn_frame, text="Cancel", command=alert_box.destroy, bg="#E2E8F0", hover_color="#CBD5E1", fg=state.FG_TEXT, font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2").pack(side=LEFT, padx=10)

    def bulk_clear_cache(self):
        selected = self.get_selected_profiles()
        if not selected:
            return
        for p in selected:
            smart_cleanup(p, state.BASE_PATH)
        show_alert(self.root, "Cleaned", "Cache cleared. Logins are safe.", "success")

    def open_multi_listing_form(self):
        selected = self.get_selected_profiles()
        if not selected:
            return

        self.form = Toplevel(self.root)
        self.form.title("Queued Listing Deployment Configurator")
        self.form.geometry("650x850")
        self.form.configure(bg=state.BG_APP)
        Frame(self.form, bg=state.BTN_ORANGE, height=6).pack(fill=X, side=TOP)

        notebook = ttk.Notebook(self.form)
        notebook.pack(fill=BOTH, expand=True, padx=15, pady=15)
        def _on_mousewheel_tabs(event):
            canvas_to_scroll = None
            if str(event.widget).startswith(str(tab1_canvas)):
                canvas_to_scroll = tab1_canvas
            elif str(event.widget).startswith(str(tab2_canvas)):
                canvas_to_scroll = tab2_canvas
            elif str(event.widget).startswith(str(tab3_canvas)):
                canvas_to_scroll = tab3_canvas

            if canvas_to_scroll:
                if hasattr(event, "delta") and event.delta:
                    canvas_to_scroll.yview_scroll(int(-1*(event.delta/120)), "units")
                elif hasattr(event, "num"):
                    if event.num == 4:
                        canvas_to_scroll.yview_scroll(-1, "units")
                    elif event.num == 5:
                        canvas_to_scroll.yview_scroll(1, "units")

        tab1_base = Frame(notebook, bg=state.BG_PANEL)
        notebook.add(tab1_base, text=" Basic Configuration ")
        tab1_canvas = Canvas(tab1_base, bg=state.BG_PANEL, highlightthickness=0)
        tab1_scrollbar = Scrollbar(tab1_base, orient="vertical", command=tab1_canvas.yview)
        tab1 = Frame(tab1_canvas, bg=state.BG_PANEL)
        tab1.bind("<Configure>", lambda e: tab1_canvas.configure(scrollregion=tab1_canvas.bbox("all")))
        tab1_canvas.create_window((0, 0), window=tab1, anchor="nw")
        tab1_canvas.configure(yscrollcommand=tab1_scrollbar.set)
        tab1_canvas.bind("<MouseWheel>", _on_mousewheel_tabs)
        tab1_canvas.bind("<Button-4>", _on_mousewheel_tabs)
        tab1_canvas.bind("<Button-5>", _on_mousewheel_tabs)
        tab1.bind("<MouseWheel>", _on_mousewheel_tabs)
        tab1.bind("<Button-4>", _on_mousewheel_tabs)
        tab1.bind("<Button-5>", _on_mousewheel_tabs)
        tab1_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        tab1_scrollbar.pack(side=RIGHT, fill=Y)

        tab2_base = Frame(notebook, bg=state.BG_PANEL)
        notebook.add(tab2_base, text=" Taxonomy & Description ")
        tab2_canvas = Canvas(tab2_base, bg=state.BG_PANEL, highlightthickness=0)
        tab2_scrollbar = Scrollbar(tab2_base, orient="vertical", command=tab2_canvas.yview)
        tab2 = Frame(tab2_canvas, bg=state.BG_PANEL)
        tab2.bind("<Configure>", lambda e: tab2_canvas.configure(scrollregion=tab2_canvas.bbox("all")))
        tab2_canvas.create_window((0, 0), window=tab2, anchor="nw")
        tab2_canvas.configure(yscrollcommand=tab2_scrollbar.set)
        tab2_canvas.bind("<MouseWheel>", _on_mousewheel_tabs)
        tab2_canvas.bind("<Button-4>", _on_mousewheel_tabs)
        tab2_canvas.bind("<Button-5>", _on_mousewheel_tabs)
        tab2.bind("<MouseWheel>", _on_mousewheel_tabs)
        tab2.bind("<Button-4>", _on_mousewheel_tabs)
        tab2.bind("<Button-5>", _on_mousewheel_tabs)
        tab2_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        tab2_scrollbar.pack(side=RIGHT, fill=Y)

        tab3_base = Frame(notebook, bg=state.BG_PANEL)
        notebook.add(tab3_base, text=" Settings & Deploy ")
        tab3_canvas = Canvas(tab3_base, bg=state.BG_PANEL, highlightthickness=0)
        tab3_scrollbar = Scrollbar(tab3_base, orient="vertical", command=tab3_canvas.yview)
        tab3 = Frame(tab3_canvas, bg=state.BG_PANEL)
        tab3.bind("<Configure>", lambda e: tab3_canvas.configure(scrollregion=tab3_canvas.bbox("all")))
        tab3_canvas.create_window((0, 0), window=tab3, anchor="nw")
        tab3_canvas.configure(yscrollcommand=tab3_scrollbar.set)
        tab3_canvas.bind("<MouseWheel>", _on_mousewheel_tabs)
        tab3_canvas.bind("<Button-4>", _on_mousewheel_tabs)
        tab3_canvas.bind("<Button-5>", _on_mousewheel_tabs)
        tab3.bind("<MouseWheel>", _on_mousewheel_tabs)
        tab3.bind("<Button-4>", _on_mousewheel_tabs)
        tab3.bind("<Button-5>", _on_mousewheel_tabs)
        tab3_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        tab3_scrollbar.pack(side=RIGHT, fill=Y)



        # Tab 1
        Label(tab1, text="Product Title:", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15,0), padx=15)
        self.title_ent = Entry(tab1, width=60, font=("Segoe UI", 10))
        self.title_ent.pack(padx=15, pady=5)

        Label(tab1, text="Product Price:", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(10,0))
        self.price_ent = Entry(tab1, width=60, font=("Segoe UI", 10))
        self.price_ent.pack(padx=15, pady=5)

        Label(tab1, text="Product Visual Assets (Multiple Images):", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15,0), padx=15)

        img_actions_frame = Frame(tab1, bg=state.BG_PANEL)
        img_actions_frame.pack(fill=X, padx=15)
        HoverButton(img_actions_frame, text="+ Add Image Files", hover_color="#F1F5F9", command=self.pick_multi_images, bg=state.BG_PANEL, fg=state.BTN_BLUE, font=("Segoe UI", 9, "bold"), relief="solid", bd=1, padx=10, cursor="hand2").pack(side=LEFT, pady=10)
        HoverButton(img_actions_frame, text="Clear All", hover_color="#FEF2F2", command=self.clear_all_images, bg=state.BG_PANEL, fg=state.BTN_RED, font=("Segoe UI", 9), relief="solid", bd=1, padx=10).pack(side=RIGHT, pady=10)

        thumbs_canvas_frame = Frame(tab1, bg="#F1F5F9", bd=1, relief="solid")
        thumbs_canvas_frame.pack(fill=BOTH, expand=True, padx=15, pady=10)
        self.img_paths_list = []
        self.img_tk_references = {}

        self.thumbs_canvas = Canvas(thumbs_canvas_frame, bg="#F1F5F9", highlightthickness=0)
        self.thumbs_scrollbar = Scrollbar(thumbs_canvas_frame, orient="vertical", command=self.thumbs_canvas.yview)
        self.thumbs_frame = Frame(self.thumbs_canvas, bg="#F1F5F9")

        self.thumbs_frame.bind("<Configure>", lambda e: self.thumbs_canvas.configure(scrollregion=self.thumbs_canvas.bbox("all")))
        self.thumbs_canvas.create_window((0, 0), window=self.thumbs_frame, anchor="nw")
        self.thumbs_canvas.configure(yscrollcommand=self.thumbs_scrollbar.set)

        def _on_mousewheel_thumbs(event):
            if hasattr(event, "delta") and event.delta:
                self.thumbs_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif hasattr(event, "num"):
                if event.num == 4:
                    self.thumbs_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.thumbs_canvas.yview_scroll(1, "units")

        self.thumbs_canvas.bind("<MouseWheel>", _on_mousewheel_thumbs)
        self.thumbs_canvas.bind("<Button-4>", _on_mousewheel_thumbs)
        self.thumbs_canvas.bind("<Button-5>", _on_mousewheel_thumbs)
        self.thumbs_frame.bind("<MouseWheel>", _on_mousewheel_thumbs)
        self.thumbs_frame.bind("<Button-4>", _on_mousewheel_thumbs)
        self.thumbs_frame.bind("<Button-5>", _on_mousewheel_thumbs)

        self.thumbs_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.thumbs_scrollbar.pack(side=RIGHT, fill=Y)

        # Tab 2
        Label(tab2, text="Marketplace Category:", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15,0), padx=15)
        self.cat_var = StringVar(tab2)
        self.cat_var.set(state.CATEGORIES[0])
        ttk.Combobox(tab2, textvariable=self.cat_var, values=state.CATEGORIES, state="readonly", width=58).pack(padx=15, pady=5)

        Label(tab2, text="Condition Status:", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(10,0))
        self.cond_var = StringVar(tab2)
        self.cond_var.set(state.CONDITIONS[0])
        ttk.Combobox(tab2, textvariable=self.cond_var, values=state.CONDITIONS, state="readonly", width=58).pack(padx=15, pady=5)

        Label(tab2, text="Listing Description:", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(10,0))
        self.desc_ent = Text(tab2, width=54, height=7, font=("Segoe UI", 10), bd=1, relief="solid", highlightcolor=state.BORDER_COLOR)
        self.desc_ent.pack(padx=15, pady=5)

        Label(tab2, text="Search Tags (Comma separated):", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(10,0))
        self.tags_ent = Entry(tab2, width=60, font=("Segoe UI", 10))
        self.tags_ent.pack(padx=15, pady=5)

        # Tab 3
        Label(tab3, text="Geographic Location Strategy:", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15,0), padx=15)
        self.loc_strategy = StringVar(value="manual")
        Radiobutton(tab3, text="Manual City Entry:", variable=self.loc_strategy, value="manual", bg=state.BG_PANEL, font=("Segoe UI", 10)).pack(anchor="w", padx=25, pady=(5,0))
        self.loc_ent = Entry(tab3, width=54, font=("Segoe UI", 10))
        self.loc_ent.pack(padx=25)

        Radiobutton(tab3, text="Auto-Randomize from list per profile", variable=self.loc_strategy, value="list", bg=state.BG_PANEL, font=("Segoe UI", 10)).pack(anchor="w", padx=25, pady=(10,0))

        list_loc_frame = Frame(tab3, bg=state.BG_PANEL)
        list_loc_frame.pack(fill=X, padx=25)
        HoverButton(list_loc_frame, text="Browse Locations Text File (.txt)", hover_color="#CBD5E1", command=self.pick_multi_listing_loc_file, bg="#E2E8F0", fg=state.FG_TEXT, font=("Segoe UI", 9), relief="solid", bd=1, padx=10, cursor="hand2").pack(side=LEFT, pady=5)

        self.lbl_loc_file_status = Label(list_loc_frame, text="Status: Manual Strategy Enabled", bg=state.BG_PANEL, fg=state.BTN_BLUE, font=("Segoe UI", 9))
        self.lbl_loc_file_status.pack(side=LEFT, padx=10)

        Label(tab3, text="Fulfillment Preferences:", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(20,0), padx=15)
        self.avail_var = StringVar(tab3)
        self.avail_var.set(state.AVAILABILITY[0])
        ttk.Combobox(tab3, textvariable=self.avail_var, values=state.AVAILABILITY, state="readonly", width=53).pack(padx=15, pady=5)

        self.meet_pub = BooleanVar()
        Checkbutton(tab3, text="Public Meetup", variable=self.meet_pub, bg=state.BG_PANEL, font=("Segoe UI", 10)).pack(anchor="w", padx=25)
        self.meet_door = BooleanVar()
        Checkbutton(tab3, text="Door Pickup", variable=self.meet_door, bg=state.BG_PANEL, font=("Segoe UI", 10)).pack(anchor="w", padx=25)

        Label(tab3, text="Templates Management:", bg=state.BG_PANEL, fg=state.FG_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(25,0), padx=15)
        templ_frame = Frame(tab3, bg=state.BG_PANEL)
        templ_frame.pack(fill=X, pady=5, padx=15)
        HoverButton(templ_frame, text="📂 Load Config Template", command=self.load_listing_config_template, bg=state.BTN_PURPLE, hover_color=state.BTN_PURPLE_HOVER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2").pack(side=LEFT, expand=True, fill=X, padx=5)
        HoverButton(templ_frame, text="💾 Save Current Config", command=self.save_listing_config_template, bg=state.BTN_ORANGE, hover_color=state.BTN_ORANGE_HOVER, fg="white", font=("Segoe UI", 10), relief="flat", cursor="hand2").pack(side=RIGHT, expand=True, fill=X, padx=5)

        HoverButton(tab3, text="➕ ADD TO MULTI-DEPLOY QUEUE", bg=state.BTN_ORANGE, hover_color=state.BTN_ORANGE_HOVER, fg="white", font=("Segoe UI", 12, "bold"), height=2, cursor="hand2", command=lambda: self.commit_bulk_listing_task(selected)).pack(fill=X, padx=10, pady=20, side=BOTTOM)

    def pick_multi_listing_loc_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")], parent=self.form)
        if path:
            self.multi_listing_loc_file_path = path
            self.lbl_loc_file_status.config(text=f"List Loaded: {os.path.basename(path)}")
            self.loc_strategy.set("list")

    def pick_multi_images(self):
        paths = filedialog.askopenfilenames(parent=self.form)
        if paths:
            self.img_paths_list.extend(list(paths))
            self.refresh_image_panel()

    def clear_all_images(self):
        self.img_paths_list.clear()
        self.refresh_image_panel()

    def remove_single_image(self, index):
        self.img_paths_list.pop(index)
        self.refresh_image_panel()

    def refresh_image_panel(self):
        for widget in self.thumbs_frame.winfo_children():
            widget.destroy()
        self.img_tk_references.clear()

        if not self.img_paths_list:
            Label(self.thumbs_frame, text="0 Visual Assets Provided", bg="#F1F5F9", fg=state.BTN_RED, font=("Segoe UI", 10, "bold")).pack(pady=20, anchor="center")
            return

        for i, path in enumerate(self.img_paths_list):
            filename = os.path.basename(path)
            container = Frame(self.thumbs_frame, bg="#F1F5F9", bd=1, relief="flat")
            container.pack(fill=X, pady=2)

            try:
                pil_image = Image.open(path)
                pil_image.thumbnail((32, 32))
                tk_image = ImageTk.PhotoImage(pil_image)
                self.img_tk_references[i] = tk_image
                Label(container, image=tk_image, bg="#F1F5F9").pack(side=LEFT, padx=5)
            except Exception as e:
                Label(container, text="🖼️", bg="#F1F5F9", font=("Segoe UI", 12)).pack(side=LEFT, padx=5)

            Label(container, text=f"({i+1}) {filename}", font=("Segoe UI", 9), fg=state.FG_TEXT, bg="#F1F5F9", anchor="w").pack(side=LEFT, padx=5, expand=True, fill=X)
            HoverButton(container, text="✕", command=lambda idx=i: self.remove_single_image(idx), bg=state.BG_PANEL, hover_color="#FEF2F2", fg=state.BTN_RED, font=("Arial", 9, "bold"), relief="flat", padx=8, cursor="hand2").pack(side=RIGHT, padx=5)

    def save_listing_config_template(self):
        details = {
            "title": self.title_ent.get(), "price": self.price_ent.get(), "category": self.cat_var.get(), "condition": self.cond_var.get(),
            "avail": self.avail_var.get(), "desc": self.desc_ent.get("1.0", "end-1c"), "tags": self.tags_ent.get(), "loc_strat": self.loc_strategy.get(),
            "loc": self.loc_ent.get(), "loc_f": getattr(self, 'multi_listing_loc_file_path', ""), "meet_p": self.meet_pub.get(),
            "door_p": self.meet_door.get(), "imgs": self.img_paths_list
        }
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], parent=self.form)
        if path:
            with open(path, 'w') as f:
                json.dump(details, f)
            show_alert(self.form, "Saved", "Configuration deployed to file securely.", "success")

    def load_listing_config_template(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], parent=self.form)
        if path:
            with open(path, 'r') as f:
                details = json.load(f)
            self.title_ent.delete(0, 'end')
            self.title_ent.insert(0, details.get("title", ""))

            self.price_ent.delete(0, 'end')
            self.price_ent.insert(0, details.get("price", ""))

            self.cat_var.set(details.get("category", state.CATEGORIES[0]))
            self.cond_var.set(details.get("condition", state.CONDITIONS[0]))
            self.avail_var.set(details.get("avail", state.AVAILABILITY[0]))

            self.desc_ent.delete("1.0", 'end')
            self.desc_ent.insert("1.0", details.get("desc", ""))

            self.tags_ent.delete(0, 'end')
            self.tags_ent.insert(0, details.get("tags", ""))

            self.loc_strategy.set(details.get("loc_strat", "manual"))

            self.loc_ent.delete(0, 'end')
            self.loc_ent.insert(0, details.get("loc", ""))

            self.multi_listing_loc_file_path = details.get("loc_f", "")
            if self.multi_listing_loc_file_path:
                self.lbl_loc_file_status.config(text=f"List Loaded: {os.path.basename(self.multi_listing_loc_file_path)}")

            self.meet_pub.set(details.get("meet_p", False))
            self.meet_door.set(details.get("door_p", False))

            self.img_paths_list = details.get("imgs", [])
            self.refresh_image_panel()

    def commit_bulk_listing_task(self, profiles):
        strat = self.loc_strategy.get()
        details = {
            "title": self.title_ent.get(), "price": self.price_ent.get(), "category": self.cat_var.get(),
            "condition": self.cond_var.get(), "availability": self.avail_var.get(), "desc": self.desc_ent.get("1.0", "end-1c"),
            "tags": self.tags_ent.get(), "public_meetup": self.meet_pub.get(), "door_pickup": self.meet_door.get(), "images": self.img_paths_list
        }

        if not details["title"] or not details["images"]:
            show_alert(self.form, "Deployment Error", "Listing requires Title and Visual Assets (Images). Provide them.", "error")
            return

        if strat == "manual":
            details["location"] = self.loc_ent.get()
        else:
            if not hasattr(self, 'multi_listing_loc_file_path') or not self.multi_listing_loc_file_path:
                show_alert(self.form, "Strategy Error", "List strategy selected but no text file provided. Switch to manual or provide file.", "error")
                return
            details["loc_type"] = "file"
            details["loc_file"] = self.multi_listing_loc_file_path
            details["loc_random"] = True

        self.form.destroy()
        self.add_automated_to_queue(profiles, "listing", details)
