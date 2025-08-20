import sys
import os

# --- Hide console window on Windows when running as .exe ---
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0
        )
    except Exception:
        pass

import subprocess
import threading
import base64
import re
from queue import Queue
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

# ----------------------------
# Config / Globals
# ----------------------------
APP_TITLE = "Wallpaper Engine Workshop Downloader"
WORKSHOP_APP_ID = "431960"  # Wallpaper Engine
current_process = None  # for cancellation

# Thread-safe UI logging queue
log_queue = Queue()

# Save location (None until loaded/selected)
save_location = None

# DepotDownloader path (auto-detected or manually set)
DEPOT_EXE_PATH = None

# Accounts and passwords (Base64 -> plain)
accounts = {
    'ruiiixx': 'UzY3R0JUQjgzRDNZ',
    'premexilmenledgconis': 'M3BYYkhaSmxEYg==',
    'vAbuDy': 'Qm9vbHE4dmlw',
    'adgjl1182': 'UUVUVU85OTk5OQ==',
    'gobjj16182': 'enVvYmlhbzgyMjI=',
    '787109690': 'SHVjVXhZTVFpZzE1'
}
passwords = {u: base64.b64decode(b64).decode("utf-8") for u, b64 in accounts.items()}


# ----------------------------
# Logging
# ----------------------------
def printlog(text: str, tag="info"):
    log_queue.put((text, tag))


def pump_logs():
    try:
        while not log_queue.empty():
            msg, tag = log_queue.get_nowait()
            console.config(state=tk.NORMAL)
            console.insert(tk.END, msg, tag)
            console.yview(tk.END)
            console.config(state=tk.DISABLED)
    finally:
        root.after(50, pump_logs)


def clear_console():
    console.config(state=tk.NORMAL)
    console.delete("1.0", tk.END)
    console.config(state=tk.DISABLED)


# ----------------------------
# Save location
# ----------------------------
def validate_save_location(path: str) -> bool:
    if not path or not os.path.isdir(path):
        printlog("Error: Save location does not exist.\n", "error")
        return False
    return True


def select_save_location():
    selected_directory = filedialog.askdirectory()
    if not selected_directory:
        return
    if validate_save_location(selected_directory):
        global save_location
        save_location = selected_directory
        with open('lastsavelocation.cfg', 'w') as f:
            f.write(selected_directory)
        printlog(f"Path set to {selected_directory}\n", "success")
        save_location_label.config(text=f"Save path: {save_location}")


def load_save_location():
    global save_location
    try:
        with open('lastsavelocation.cfg', 'r') as f:
            candidate = f.read().strip()
            if validate_save_location(candidate):
                save_location = candidate
            else:
                save_location = None
    except FileNotFoundError:
        save_location = None


def resolve_pubfile_dir(path: str, pubfileid: str) -> str:
    pub_dir = os.path.join(path, pubfileid)
    os.makedirs(pub_dir, exist_ok=True)
    return pub_dir


# ----------------------------
# DepotDownloader Path Handling
# ----------------------------
def validate_depot_path(path: str) -> bool:
    return path and os.path.isfile(path) and path.lower().endswith(".exe")


def auto_detect_depot():
    """Try to auto-detect DepotDownloadermod.exe in common paths, PATH, and drives"""
    global DEPOT_EXE_PATH

    # 1. Load from config if saved
    try:
        with open("lastdepot.cfg", "r") as f:
            candidate = f.read().strip()
            if validate_depot_path(candidate):
                DEPOT_EXE_PATH = candidate
                return
    except FileNotFoundError:
        pass

    # 2. Check current directory
    candidate = os.path.join(os.getcwd(), "DepotDownloadermod.exe")
    if validate_depot_path(candidate):
        DEPOT_EXE_PATH = candidate
        return

    # 3. Check PATH
    for p in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(p, "DepotDownloadermod.exe")
        if validate_depot_path(candidate):
            DEPOT_EXE_PATH = candidate
            return

    # 4. Scan drives (Windows only)
    if sys.platform == "win32":
        for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_root = f"{drive}:\\"
            for rootdir, _, files in os.walk(drive_root):
                if "DepotDownloadermod.exe" in files:
                    DEPOT_EXE_PATH = os.path.join(rootdir, "DepotDownloadermod.exe")
                    return


def select_depot_path():
    global DEPOT_EXE_PATH
    selected_file = filedialog.askopenfilename(
        title="Select DepotDownloadermod.exe",
        filetypes=[("Executable", "*.exe")]
    )
    if selected_file and validate_depot_path(selected_file):
        DEPOT_EXE_PATH = selected_file
        with open("lastdepot.cfg", "w") as f:
            f.write(selected_file)
        printlog(f"DepotDownloader path set to {selected_file}\n", "success")
        depot_path_label.config(text=f"Depot path: {DEPOT_EXE_PATH}")
    else:
        messagebox.showerror("Error", "Invalid file selected.")


# ----------------------------
# Download Process
# ----------------------------
def run_command(pubfileid: str):
    global current_process
    printlog(f"\n---------- Downloading {pubfileid} ----------\n", "download")

    if save_location is None:
        printlog("Error: Save location is not set.\n", "error")
        return
    if not validate_save_location(save_location):
        return

    if not validate_depot_path(DEPOT_EXE_PATH):
        printlog("Error: DepotDownloadermod.exe not found. Please set it.\n", "error")
        return

    pubfile_directory = resolve_pubfile_dir(save_location, pubfileid)

    try:
        user = username.get()
        pwd = passwords[user]
    except Exception:
        printlog("Error: Invalid/unknown username selected.\n", "error")
        return

    cmd = [
        DEPOT_EXE_PATH,
        "-app", WORKSHOP_APP_ID,
        "-pubfile", pubfileid,
        "-verify-all",
        "-username", user,
        "-password", pwd,
        "-dir", pubfile_directory
    ]

    try:
        current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
    except Exception as e:
        printlog(f"Error starting process: {e}\n", "error")
        return

    try:
        for line in current_process.stdout:
            printlog(line, "info")
    finally:
        if current_process.stdout:
            current_process.stdout.close()
        current_process.wait()

    printlog("------------- Download finished -----------\n", "success")
    current_process = None


def run_commands():
    set_run_buttons_state(disabled=True)
    try:
        links = link_text.get("1.0", tk.END).splitlines()
        pattern = re.compile(r'\b\d{8,10}\b')
        any_started = False

        for raw in links:
            link = raw.strip()
            if not link:
                continue
            match = pattern.search(link)
            if match:
                any_started = True
                progress_var.set(0)
                progress_bar.start(20)
                run_command(match.group(0))
            else:
                printlog(f"Invalid link: {link}\n", "error")

        if not any_started:
            printlog("No valid workshop file IDs found.\n", "error")

    except Exception as e:
        printlog(f"Unexpected error: {e}\n", "error")
    finally:
        progress_bar.stop()
        progress_var.set(100)
        set_run_buttons_state(disabled=False)


def start_thread():
    t = threading.Thread(target=run_commands, daemon=True)
    t.start()


def cancel_download():
    global current_process
    if current_process:
        try:
            current_process.kill()
            printlog("Download canceled by user.\n", "error")
            current_process = None
        except Exception as e:
            printlog(f"Failed to cancel: {e}\n", "error")


# ----------------------------
# Helpers
# ----------------------------
def paste_clipboard():
    try:
        data = root.clipboard_get()
        link_text.insert(tk.END, data + "\n")
    except Exception:
        messagebox.showerror("Error", "Clipboard is empty or not accessible.")


def set_run_buttons_state(disabled: bool):
    state = tk.DISABLED if disabled else tk.NORMAL
    run_button.config(state=state)
    cancel_button.config(state=(tk.NORMAL if disabled else tk.DISABLED))


def on_closing():
    cancel_download()
    root.destroy()


# ----------------------------
# UI Setup
# ----------------------------
load_save_location()
auto_detect_depot()

root = tk.Tk()
root.title(APP_TITLE)
root.geometry("750x750")
root.option_add("*Font", "SegoeUI 10")

# --- Title ---
title_label = ttk.Label(root, text=APP_TITLE, font=("SegoeUI", 18, "bold"))
title_label.pack(pady=10)

# --- Account Section ---
frame_account = ttk.LabelFrame(root, text="Account")
frame_account.pack(fill="x", padx=10, pady=5)

username = tk.StringVar(root)
username.set(list(accounts.keys())[0])
username_menu = ttk.OptionMenu(
    frame_account,
    username,
    list(accounts.keys())[0],
    *accounts.keys()
)
username_menu.pack(side="left", padx=5, pady=5)

# --- Depot Path Section ---
frame_depot = ttk.LabelFrame(root, text="DepotDownloader Path")
frame_depot.pack(fill="x", padx=10, pady=5)

depot_button = ttk.Button(frame_depot, text="Select DepotDownloader Path", command=select_depot_path)
depot_button.pack(side="left", padx=5, pady=5)

depot_path_label = ttk.Label(frame_depot, text=f"Depot path: {DEPOT_EXE_PATH if DEPOT_EXE_PATH else 'Not set'}")
depot_path_label.pack(side="left", padx=5, pady=5)

# --- Save Location Section ---
frame_path = ttk.LabelFrame(root, text="Save Location")
frame_path.pack(fill="x", padx=10, pady=5)

save_location_button = ttk.Button(frame_path, text="Select Save Path", command=select_save_location)
save_location_button.pack(side="left", padx=5, pady=5)

save_location_label = ttk.Label(frame_path, text=f"Save path: {save_location if save_location else 'Not set'}")
save_location_label.pack(side="left", padx=5, pady=5)

# --- Links Section ---
frame_links = ttk.LabelFrame(root, text="Workshop Links")
frame_links.pack(fill="both", expand=True, padx=10, pady=5)

link_text = scrolledtext.ScrolledText(frame_links, height=8, width=70)
link_text.pack(padx=5, pady=5, fill="both", expand=True)

btn_frame = ttk.Frame(frame_links)
btn_frame.pack(fill="x", pady=5)

paste_button = ttk.Button(btn_frame, text="Paste from Clipboard", command=paste_clipboard)
paste_button.pack(side="left", padx=5)

clear_input_button = ttk.Button(btn_frame, text="Clear Input", command=lambda: link_text.delete("1.0", tk.END))
clear_input_button.pack(side="left", padx=5)

# --- Console Section ---
frame_console = ttk.LabelFrame(root, text="Console Output")
frame_console.pack(fill="both", expand=True, padx=10, pady=5)

console = scrolledtext.ScrolledText(frame_console, height=12, width=70, state=tk.DISABLED, bg="black", fg="white")
console.pack(fill="both", expand=True, padx=5, pady=5)

console.tag_config("info", foreground="white")
console.tag_config("error", foreground="red")
console.tag_config("success", foreground="green")
console.tag_config("download", foreground="green")

clear_console_button = ttk.Button(frame_console, text="Clear Console", command=clear_console)
clear_console_button.pack(pady=5)

# --- Progress + Controls ---
frame_controls = ttk.Frame(root)
frame_controls.pack(fill="x", padx=10, pady=10)

progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(frame_controls, orient="horizontal", length=400, mode="determinate", variable=progress_var)
progress_bar.pack(side="left", padx=5, pady=5)

run_button = ttk.Button(frame_controls, text="Download", command=start_thread)
run_button.pack(side="left", padx=5)

cancel_button = ttk.Button(frame_controls, text="Cancel", command=cancel_download, state=tk.DISABLED)
cancel_button.pack(side="left", padx=5)

# --- Window events ---
root.protocol("WM_DELETE_WINDOW", on_closing)
pump_logs()

root.mainloop()