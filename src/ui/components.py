from concurrent.futures import ThreadPoolExecutor
from tkinter import Toplevel, Frame, Label, Button, X, TOP
import src.state as state
from src.utils.system_utils import play_success_sound
from src.automation.worker import worker_task

class HoverButton(Button):
    def __init__(self, master, hover_color=None, **kw):
        Button.__init__(self, master=master, **kw)
        self.defaultBackground = self["bg"]
        self.hoverBackground = hover_color if hover_color else self.defaultBackground
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.hoverBackground

    def on_leave(self, e):
        self['bg'] = self.defaultBackground

def show_alert(parent, title, message, alert_type="info"):
    alert = Toplevel(parent)
    alert.title(title)
    alert.geometry("400x180")
    alert.configure(bg=state.BG_PANEL)
    alert.transient(parent)
    alert.grab_set()

    color = state.BTN_GREEN if alert_type == "success" else state.BTN_RED if alert_type == "error" else state.BTN_BLUE
    Frame(alert, bg=color, height=6).pack(fill=X, side=TOP)

    Label(alert, text=title, font=("Segoe UI", 12, "bold"), bg=state.BG_PANEL, fg=color).pack(pady=(15, 5))
    Label(alert, text=message, font=("Segoe UI", 10), bg=state.BG_PANEL, fg=state.FG_TEXT, wraplength=360, justify="center").pack(pady=5)
    HoverButton(alert, text="OK", command=alert.destroy, bg=color, hover_color=color, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", width=12, cursor="hand2").pack(pady=10)

    alert.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (180 // 2)
    alert.geometry(f"+{x}+{y}")
    parent.wait_window(alert)

import time

def execute_queue_automated(threads, root_window, progress_bar, update_ui_callback, status_label=None):
    state.GLOBAL_STOP = False
    total_tasks = len(state.TASK_QUEUE)

    if total_tasks == 0:
        return

    completed = 0
    start_time = time.time()

    def update_progress(p_name=None, t_type=None):
        nonlocal completed
        completed += 1

        # Calculate ETA
        elapsed = time.time() - start_time
        if completed > 0:
            avg_time_per_task = elapsed / completed
            remaining_tasks = total_tasks - completed
            eta_seconds = int(avg_time_per_task * remaining_tasks)

            # Formatting ETA
            if eta_seconds > 3600:
                eta_str = f"{eta_seconds // 3600}h {(eta_seconds % 3600) // 60}m"
            elif eta_seconds > 60:
                eta_str = f"{eta_seconds // 60}m {eta_seconds % 60}s"
            else:
                eta_str = f"{eta_seconds}s"
        else:
            eta_str = "Calculating..."

        progress_val = (completed / total_tasks) * 100

        def ui_update():
            progress_bar.config(value=progress_val)
            if status_label:
                status_txt = f"Progress: {completed}/{total_tasks} | ETA: {eta_str}"
                if p_name:
                    status_txt += f" | Just Finished: {p_name} ({t_type})"
                status_label.config(text=status_txt)

        root_window.after(0, ui_update)

    print(f"\n[QUEUE] Dispatching {total_tasks} operations via {threads} threads...\n")

    if status_label:
        root_window.after(0, lambda: status_label.config(text=f"Starting {total_tasks} tasks..."))

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for task in state.TASK_QUEUE:
            if state.GLOBAL_STOP:
                break

            p_name, t_type = task[0], task[1]

            # Wrap the callback to include profile info
            def make_callback(pn, tt):
                return lambda: update_progress(pn, tt)

            future = executor.submit(worker_task, p_name, t_type, task[2], task[3], task[4], make_callback(p_name, t_type))
            futures.append(future)

    if not state.GLOBAL_STOP:
        play_success_sound()
        root_window.after(0, lambda: show_alert(root_window, "Execution Complete", "All queued tasks finished successfully!", "success"))
    else:
        root_window.after(0, lambda: show_alert(root_window, "Process Halted", "Execution stopped forcefully.", "error"))

    state.TASK_QUEUE.clear()
    root_window.after(0, lambda: progress_bar.config(value=0))
    if status_label:
        root_window.after(0, lambda: status_label.config(text="Idle"))
    root_window.after(0, update_ui_callback)
