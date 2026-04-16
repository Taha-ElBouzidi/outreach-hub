"""
outreach_hub_v9.py
-------------------
Evernex Outreach Hub - V9.0
Debugged layout fixing scrolling, integrating 60FPS overlay curtains, 
and adopting requested CTkSwitch & heavy burgundy palette.
"""

import os
import sys
import json
import csv
import queue
import threading
import subprocess
import time
import random
import urllib.request
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- DEPENDENCY SIGNALS FOR PYINSTALLER ---
import selenium
from selenium import webdriver
import webdriver_manager
# ------------------------------------------

# ==========================================================================
# CONFIG
# ==========================================================================
APP_VERSION = "9.0"
LI_PORT = 9222
OL_PORT = 9223
GM_PORT = 9224

MIN_DELAY = 5
MAX_DELAY = 10

# ==========================================================================
# THEME — Deep Burgundy & Soft Gold (No White)
# ==========================================================================
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg_dark":       "#ffe6a7",    # Cream background for whole app
    "bg_sidebar":    "#6f1d1b",    # Heavy Burgundy Sidebar
    "bg_card":       "#bb9457",    # Soft Gold Cards (Replaced White)
    "bg_input":      "#f0d89c",    # Muted Cream inputs 
    "accent":        "#432818",    # Cocoa Action Buttons
    "accent_hover":  "#99582a",    # Sienna Action Hover
    "accent_glow":   "#99582a",    
    "green":         "#432818",    # Cocoa 
    "green_hover":   "#6f1d1b",    
    "red":           "#6f1d1b",    # Burgundy
    "red_hover":     "#432818",    
    "text_primary":  "#432818",    # Dark Cocoa Text on Cream/Gold
    "text_secondary":"#432818",    
    "text_muted":    "#6f1d1b",    
    "text_sidebar":  "#ffe6a7",    # Cream text on Burgundy Sidebar
    "border":        "#99582a",    # Sienna border
    "linkedin":      "#ffe6a7",    # Make icons match the aesthetic
    "outlook":       "#ffe6a7",
    "gmail":         "#ffe6a7",
}

DYNAMIC_VARS = [
    ("[first_name]", "First Name"),
    ("[last_name]", "Last Name"),
    ("[company]", "Company"),
    ("[job_title]", "Job Title"),
    ("[city]", "City"),
]

# ==========================================================================
# GLOBAL UTILITIES
# ==========================================================================
def get_chrome_path():
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe")
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

# ==========================================================================
# ENGINE LOADING
# ==========================================================================
if getattr(sys, 'frozen', False):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    sys.path.append(base_path)
else:
    base_path = os.path.dirname(__file__)
    sys.path.append(os.path.join(base_path, "..", "01_Engines"))

ol_eng = None
li_eng = None
gm_eng = None
csv_parser = None
acct_mgr = None

def load_engines():
    global ol_eng, li_eng, gm_eng, csv_parser, acct_mgr
    try:
        import outlook_engine as _ol
        import link as _li
        import gmail_engine as _gm
        import csv_parser as _csv
        import account_manager as _am
        ol_eng = _ol
        li_eng = _li
        gm_eng = _gm
        csv_parser = _csv
        acct_mgr = _am
        return True
    except Exception as e:
        print(f"Engine Load Error: {e}")
        return False

try:
    import account_manager as acct_mgr
except ImportError:
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "01_Engines"))
        import account_manager as acct_mgr
    except:
        acct_mgr = None

# ==========================================================================
# DEFAULT TEMPLATES
# ==========================================================================
DEFAULT_TEMPLATES = {
    "LinkedIn": "Hi [first_name], I noticed your work at [company]. I am with Evernex, a Global TPM Provider. I would love to connect and share some insights. Best,",
    "Email": {
        "subject": "Global hardware lifecycle support for [company]",
        "body": (
            "Hi [first_name],\n\n"
            "I am reaching out from Evernex, a Global TPM Provider. "
            "Eliminate the chain-of-custody risk with onsite NIST 800-compliant shredding.\n\n"
            "Best regards,"
        )
    }
}

# ==========================================================================
# WORKER THREAD
# ==========================================================================
def hub_worker(account, mode, data, file_path, log_q, stop_event, campaign_type, template_subj, template_body):
    if not load_engines():
        log_q.put(("error", "Critical: Could not load automation engines.", 0, 0))
        return
        
    import datetime
    start_time = datetime.datetime.now()

    if mode == "LinkedIn":
        pending = [(i, p) for i, p in enumerate(data) if p.get("connection_status", "") not in ["sent", "done"]]
    else:
        pending = [(i, p) for i, p in enumerate(data) if p.get("status", "pending") in ["pending", "error"]]

    total = len(pending)
    can_start, err_msg = account.can_send(total)
    
    if not can_start:
        log_q.put(("error", f"Quota Exceeded: {err_msg}", 0, 0))
        return

    log_q.put(("start", f"Starting {mode} ({campaign_type}) — {total} prospects", 0, total))

    if total == 0:
        log_q.put(("done", "No items to process.", 0, 0))
        return

    try:
        port = LI_PORT if mode == "LinkedIn" else (OL_PORT if mode == "Outlook" else GM_PORT)
        driver = ol_eng.get_driver(port=port)

        if mode == "Outlook" and not ol_eng.switch_to_outlook(driver):
            log_q.put(("error", "Outlook tab not found in browser.", 0, 0))
            return
        if mode == "Gmail" and not gm_eng.switch_to_gmail(driver):
            log_q.put(("error", "Gmail tab not found in browser.", 0, 0))
            return
    except Exception as e:
        log_q.put(("error", f"Browser Connection Failed: {str(e)}", 0, total))
        return

    engine = ol_eng if mode == "Outlook" else (gm_eng if mode == "Gmail" else None)
    count = 0

    for idx, (data_idx, p) in enumerate(pending):
        if stop_event.is_set():
            log_q.put(("stopped", f"Paused by user. Completed {count}/{total}.", count, total))
            return

        name = (p.get("name") or p.get("prospect_name") or
                f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or "there")
        first_name = str(name).split(" ")[0].strip()
        log_q.put(("progress", f"Processing: {name}", count, total))

        try:
            if mode == "LinkedIn":
                if campaign_type == "Sequence" and csv_parser:
                    msg = csv_parser.apply_template_variables(template_body, p)
                else:
                    msg = p.get("final_outreach", template_body.replace("[first_name]", first_name))
                status = li_eng.process_one(driver, {"linkedin_url": p.get("linkedin_url", ""), "final_outreach": msg})
                data[data_idx]["connection_status"] = status
            else:
                if campaign_type == "Sequence" and csv_parser:
                    subj = csv_parser.apply_template_variables(template_subj, p)
                    body_raw = csv_parser.apply_template_variables(template_body, p)
                else:
                    subj = p.get("email_subject", template_subj.replace("[first_name]", first_name))
                    body_raw = p.get("email_body", template_body.replace("[first_name]", first_name))

                body = ol_eng.apply_evernex_styling(body_raw) if campaign_type == "Sequence" else body_raw

                compose_fn = engine.click_new_message if mode == "Outlook" else engine.click_compose
                if compose_fn(driver):
                    time.sleep(2)
                    target_email = p.get('email') or p.get('Work Email')
                    if engine.set_recipient(driver, target_email):
                        if engine.set_subject(driver, subj):
                            if engine.set_body(driver, body):
                                if engine.click_send(driver):
                                    status = "sent"
                                else:
                                    status = "error: send_failed"
                            else:
                                status = "error: body_failed"
                        else:
                            status = "error: subject_failed"
                    else:
                        status = "error: recipient_failed"
                else:
                    status = "error: compose_failed"
                data[data_idx]["status"] = status

            if file_path and file_path.endswith(".json"):
                ol_eng.save_json(file_path, data)

            icon = "✅" if "sent" in str(status) or status == "done" else "❌"
            log_q.put(("log", f"{icon} {name} \n  ↪ Status: {status}\n", count + 1, total))
            count += 1

        except Exception as e:
            log_q.put(("log", f"❌ {name}\n  ↪ Error: {str(e)}\n", count, total))

        if idx < total - 1 and not stop_event.is_set():
            delay = random.randint(MIN_DELAY, MAX_DELAY)
            log_q.put(("log", f"⏱ Waiting {delay}s...", count, total))
            time.sleep(delay)

    duration_sec = (datetime.datetime.now() - start_time).total_seconds()
    failed = total - count
    if acct_mgr:
        acct_mgr.log_campaign_completion(account, mode, campaign_type, total, count, failed, start_time, duration_sec)

    log_q.put(("done", f"{mode} campaign complete! {count}/{total} processed.", total, total))


# ==========================================================================
# BOUTIQUE UI OUTREACH HUB V9
# ==========================================================================
class OutreachHubV9(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Evernex Outreach Hub — V{APP_VERSION} (Boutique Update)")
        self.geometry("1150x800")
        self.minsize(900, 650)
        self.configure(fg_color=COLORS["bg_dark"])

        self.log_q = queue.Queue()
        self.stop_event = threading.Event()
        self.current_mode = "LinkedIn"
        self.loaded_data = []
        self.loaded_file_path = ""
        self.detected_columns = {}
        self.current_account = None

        self._check_initial_auth()

    # ------------------ LOGIN & AUTH ------------------
    def _check_initial_auth(self):
        if acct_mgr:
            saved = acct_mgr.load_session()
            if saved and saved.key:
                def verify_remotely():
                    account, err = acct_mgr.verify_session(saved)
                    if account:
                        self.current_account = account
                        acct_mgr.save_session(account)
                        self.after(0, self._render_main_ui)
                    else:
                        acct_mgr.clear_session()
                        self.after(0, self._build_login_ui)
                threading.Thread(target=verify_remotely, daemon=True).start()
                self._build_loading_ui()
                return
        self._build_login_ui()

    def _build_loading_ui(self):
        self.loading_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.loading_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(self.loading_frame, text="EVERNEX", font=ctk.CTkFont("Segoe UI", 36, weight="bold"), text_color=COLORS["text_primary"]).pack(expand=True)

    def _build_login_ui(self):
        for w in self.winfo_children(): w.destroy()
        self.login_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.login_frame.pack(fill="both", expand=True)

        card = ctk.CTkFrame(self.login_frame, fg_color=COLORS["bg_card"], corner_radius=25, width=420, height=440)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="EVERNEX", font=ctk.CTkFont("Segoe UI", 28, weight="bold"), text_color=COLORS["text_primary"]).pack(pady=(45, 3))
        
        self.username_entry = ctk.CTkEntry(card, placeholder_text="Username", width=320, height=42, corner_radius=12, fg_color=COLORS["bg_input"], border_width=0, text_color=COLORS["text_primary"])
        self.username_entry.pack(pady=(20, 8))
        
        self.key_entry = ctk.CTkEntry(card, placeholder_text="Activation Key", width=320, height=42, corner_radius=12, fg_color=COLORS["bg_input"], border_width=0, text_color=COLORS["text_primary"], show="•")
        self.key_entry.pack(pady=(0, 15))

        self.login_error = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11), text_color=COLORS["red"])
        self.login_error.pack(pady=(0, 5))

        ctk.CTkButton(card, text="SIGN IN", height=45, width=320, corner_radius=12, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), command=self._activate_license).pack()
        
    def _activate_license(self):
        username = self.username_entry.get().strip()
        key = self.key_entry.get().strip()
        self.login_error.configure(text="Verifying...", text_color=COLORS["text_primary"])
        self.update()

        if acct_mgr:
            account, err = acct_mgr.authenticate(username, key) if username else acct_mgr.authenticate_by_key_only(key)
            if account:
                self.current_account = account
                acct_mgr.save_session(account)
                self._render_main_ui()
            else:
                self.login_error.configure(text=err or "Invalid credentials.", text_color=COLORS["red"])
        else:
            self.login_error.configure(text="Account system not loaded.", text_color=COLORS["red"])

    def _logout(self):
        self.current_account = None
        if acct_mgr: acct_mgr.clear_session()
        self._build_login_ui()

    # ------------------ LAYOUT MODULAR BUILDERS ------------------
    def _render_main_ui(self):
        for w in self.winfo_children(): w.destroy()

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=COLORS["bg_sidebar"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # FIXED: Use ScrollableFrame to restore mouse scrolling
        self.content = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color=COLORS["bg_dark"])
        self.content.pack(side="right", fill="both", expand=True)

        self.build_sidebar()
        self.build_header()
        self.build_file_loader()
        self.build_config_card()
        self.build_action_row()
        self.build_log_card()

        # Place the grid items natively and instantly
        self.header.pack(fill="x", padx=30, pady=(25, 0))
        self.file_card.pack(fill="x", padx=30, pady=(15, 0))
        self.config_card.pack(fill="x", padx=30, pady=(15, 0))
        self.action_row.pack(fill="x", padx=30, pady=(15, 0))
        self.progress_frame.pack(fill="x", padx=30, pady=(10, 0))
        self.log_card.pack(fill="both", expand=True, padx=30, pady=(10, 20))
        
        self._switch_channel("LinkedIn")
        self._poll_queue()
        
        # 60FPS Native Loading Curtain
        self.curtain = ctk.CTkFrame(self, fg_color=COLORS["bg_sidebar"], corner_radius=0)
        self.curtain.place(relwidth=1, relheight=1, x=0, y=0)
        ctk.CTkLabel(self.curtain, text="EVERNEX Workspace", font=ctk.CTkFont("Segoe UI", 40, weight="bold"), text_color=COLORS["text_sidebar"]).place(relx=0.5, rely=0.5, anchor="center")
        
        # Give the GUI thread 150ms to render the grid underneath, then trigger slide
        self.after(150, self._slide_curtain_down, 0)

    def _slide_curtain_down(self, offset_y):
        """A pure 60FPS spatial slide down."""
        screen_height = self.winfo_height()
        if offset_y > screen_height:
            self.curtain.place_forget()
            self.curtain.destroy()
            return

        # 60fps smoothing using a robust downward velocity (e.g. 35 pixels per frame)
        velocity = max(25, int(screen_height * 0.05))
        self.curtain.place(y=offset_y)
        self.after(16, lambda: self._slide_curtain_down(offset_y + velocity))

    def build_sidebar(self):
        ctk.CTkLabel(self.sidebar, text="EVERNEX", font=ctk.CTkFont("Segoe UI", 20, weight="bold"), text_color=COLORS["text_sidebar"]).pack(pady=(25, 2))
        
        acct = self.current_account
        if acct:
            user_card = ctk.CTkFrame(self.sidebar, fg_color=COLORS["accent"], corner_radius=12)
            user_card.pack(fill="x", padx=15, pady=(20, 20))
            
            info_row = ctk.CTkFrame(user_card, fg_color="transparent")
            info_row.pack(fill="x", padx=10, pady=10)
            
            initial = acct.display_name[0].upper()
            ctk.CTkLabel(info_row, text=initial, width=36, height=36, corner_radius=18, fg_color=COLORS["bg_dark"], text_color=COLORS["text_primary"], font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=(0, 10))
            name_frame = ctk.CTkFrame(info_row, fg_color="transparent")
            name_frame.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(name_frame, text=acct.display_name, font=ctk.CTkFont(size=13, weight="bold"), text_color=COLORS["text_sidebar"], anchor="w").pack(anchor="w")
            ctk.CTkLabel(name_frame, text=acct.quota_label, font=ctk.CTkFont(size=10), text_color=COLORS["bg_input"], anchor="w").pack(anchor="w")

            ctk.CTkButton(user_card, text="Sign Out", height=28, corner_radius=8, fg_color="transparent", hover_color=COLORS["red"], text_color=COLORS["text_sidebar"], font=ctk.CTkFont(size=11), command=self._logout).pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.sidebar, text="CHANNELS", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["bg_card"]).pack(anchor="w", padx=20, pady=(10, 5))

        self.channel_btns = {}
        allowed = acct.channels if acct else ["LinkedIn", "Outlook", "Gmail"]
        for ch, icon in [("LinkedIn", "🔗"), ("Outlook", "📧"), ("Gmail", "📨")]:
            has_acc = ch in allowed
            btn = ctk.CTkButton(self.sidebar, text=f"  {icon}  {ch}" if has_acc else f"  🔒  {ch}", anchor="w", height=45, corner_radius=12, fg_color="transparent", hover_color=COLORS["accent"], text_color=COLORS["text_sidebar"], font=ctk.CTkFont("Segoe UI", 13), command=(lambda c=ch: self._switch_channel(c)) if has_acc else (lambda: None), state="normal" if has_acc else "disabled")
            btn.pack(fill="x", padx=15, pady=2)
            self.channel_btns[ch] = btn

    def build_header(self):
        self.header = ctk.CTkFrame(self.content, fg_color="transparent", height=50)
        self.header.grid_columnconfigure(0, weight=1)
        self.header_label = ctk.CTkLabel(self.header, text="LinkedIn Outreach", font=ctk.CTkFont("Segoe UI", 26, weight="bold"), text_color=COLORS["text_primary"], anchor="w")
        self.header_label.grid(row=0, column=0, sticky="w")
        
        self.launch_btn = ctk.CTkButton(self.header, text="Launch Browser", width=160, height=40, corner_radius=12, fg_color=COLORS["bg_card"], hover_color=COLORS["accent_hover"], text_color=COLORS["text_primary"], font=ctk.CTkFont(size=13, weight="bold"), command=self._login_action)
        self.launch_btn.grid(row=0, column=1, sticky="e")

    def build_file_loader(self):
        self.file_card = ctk.CTkFrame(self.content, fg_color=COLORS["bg_card"], corner_radius=20)
        self.file_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.file_card, text="📂 Target Data", font=ctk.CTkFont("Segoe UI", 14, weight="bold"), text_color=COLORS["text_primary"]).grid(row=0, column=0, padx=25, pady=(20, 5), sticky="w", columnspan=2)
        
        self.file_entry = ctk.CTkEntry(self.file_card, placeholder_text="Upload your CSV or JSON file...", height=42, corner_radius=12, border_width=0, fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], state="disabled")
        self.file_entry.grid(row=1, column=0, padx=(25, 10), pady=(5, 20), sticky="ew", columnspan=2)
        
        ctk.CTkButton(self.file_card, text="Browse", width=110, height=42, corner_radius=12, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["text_sidebar"], font=ctk.CTkFont(size=13, weight="bold"), command=self._browse).grid(row=1, column=2, padx=(0, 25), pady=(5, 20), sticky="e")
        
        self.file_status = ctk.CTkLabel(self.file_card, text="", font=ctk.CTkFont(size=12), text_color=COLORS["text_primary"])
        self.file_status.grid(row=2, column=0, padx=25, pady=(0, 15), sticky="w", columnspan=3)

    def build_config_card(self):
        self.config_card = ctk.CTkFrame(self.content, fg_color=COLORS["bg_card"], corner_radius=20)
        self.config_card.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.config_card, text="⚙ Strategy Mode", font=ctk.CTkFont("Segoe UI", 14, weight="bold"), text_color=COLORS["text_primary"]).grid(row=0, column=0, padx=25, pady=(20, 8), sticky="w")
        
        self.type_var = ctk.StringVar(value="Custom JSON")
        
        # Native CTkSwitch perfectly fulfills the requested "Day/Night" elegant color sliding toggle at 60FPS.
        self.mode_switch = ctk.CTkSwitch(
            self.config_card, 
            text="Mode: Custom JSON",
            variable=self.type_var,
            onvalue="Sequence", 
            offvalue="Custom JSON",
            progress_color=COLORS["red"],
            button_color=COLORS["bg_dark"], 
            button_hover_color=COLORS["bg_input"],
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            command=self._on_switch_toggle
        )
        self.mode_switch.grid(row=1, column=0, padx=25, pady=(0, 15), sticky="w")

        # Templates
        self.tmpl_frame = ctk.CTkFrame(self.config_card, fg_color="transparent")
        var_bar = ctk.CTkFrame(self.tmpl_frame, fg_color="transparent")
        var_bar.pack(fill="x", padx=25, pady=(0, 5))
        for v_code, v_label in DYNAMIC_VARS:
            ctk.CTkButton(var_bar, text=v_label, width=90, height=26, corner_radius=6, fg_color=COLORS["bg_input"], hover_color=COLORS["red"], text_color=COLORS["text_primary"], font=ctk.CTkFont(size=11), command=lambda v=v_code: self._insert_variable(v)).pack(side="left", padx=3)

        self.tmpl_subj = ctk.CTkEntry(self.tmpl_frame, placeholder_text="Subject line...", height=40, corner_radius=10, border_width=0, fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"])
        self.tmpl_subj.pack(fill="x", padx=25, pady=(8, 8))

        self.tmpl_body = ctk.CTkTextbox(self.tmpl_frame, height=140, corner_radius=10, border_width=0, fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], font=ctk.CTkFont("Segoe UI", 13))
        self.tmpl_body.pack(fill="x", padx=25, pady=(0, 20))

    def build_action_row(self):
        self.action_row = ctk.CTkFrame(self.content, fg_color="transparent")
        self.action_row.grid_columnconfigure((0, 1), weight=1)
        
        self.btn_start = ctk.CTkButton(self.action_row, text="▶ START CAMPAIGN", height=50, corner_radius=15, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["text_sidebar"], font=ctk.CTkFont("Segoe UI", 15, weight="bold"), state="disabled", command=self._start)
        self.btn_start.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_stop = ctk.CTkButton(self.action_row, text="■ STOP", height=50, corner_radius=15, fg_color=COLORS["red"], hover_color=COLORS["red_hover"], text_color=COLORS["text_sidebar"], font=ctk.CTkFont("Segoe UI", 15, weight="bold"), state="disabled", command=self._stop)
        self.btn_stop.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.progress_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.progress_frame.grid_columnconfigure(0, weight=1)
        self.status_lbl = ctk.CTkLabel(self.progress_frame, text="Ready", anchor="w", font=ctk.CTkFont("Segoe UI", 13), text_color=COLORS["text_primary"])
        self.status_lbl.grid(row=0, column=0, sticky="w")
        self.pb = ctk.CTkProgressBar(self.progress_frame, height=8, corner_radius=4, fg_color=COLORS["bg_card"], progress_color=COLORS["red"])
        self.pb.set(0)
        self.pb.grid(row=1, column=0, sticky="ew", pady=(5, 0))

    def build_log_card(self):
        self.log_card = ctk.CTkFrame(self.content, fg_color=COLORS["bg_card"], corner_radius=20, height=300)
        self.log_card.pack_propagate(False) # Prevent shrinking
        ctk.CTkLabel(self.log_card, text="📊 Live Activity Feed", font=ctk.CTkFont("Segoe UI", 14, weight="bold"), text_color=COLORS["text_primary"]).pack(anchor="w", padx=25, pady=(20, 8))
        self.txt_log = ctk.CTkTextbox(self.log_card, corner_radius=12, border_width=0, fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], font=ctk.CTkFont("Segoe UI", 13))
        self.txt_log.pack(fill="both", expand=True, padx=25, pady=(0, 25))

    # ------------------ EVENT HANDLERS ------------------
    def _switch_channel(self, channel):
        self.current_mode = channel
        
        # 60fps Wipe Animation for content swap
        self._animate_tab_wipe()
        
        for ch, btn in self.channel_btns.items():
            btn.configure(fg_color=COLORS["bg_dark"] if ch == channel else "transparent", text_color=COLORS["text_primary"] if ch == channel else COLORS["text_sidebar"])

        labels = {"LinkedIn": "LinkedIn Outreach", "Outlook": "Outlook Enterprise", "Gmail": "Gmail Prospecting"}
        if hasattr(self, 'header_label'):
            self.header_label.configure(text=labels.get(channel, channel))
        if hasattr(self, 'launch_btn'):
            self.launch_btn.configure(text=f"Launch {channel}")

        if self.type_var.get() == "Sequence":
            self._on_type_change("Sequence")

        self.tmpl_body.delete("1.0", "end")
        if channel == "LinkedIn":
            self.tmpl_body.insert("1.0", DEFAULT_TEMPLATES["LinkedIn"])
        else:
            self.tmpl_subj.delete(0, "end")
            self.tmpl_subj.insert(0, DEFAULT_TEMPLATES["Email"]["subject"])
            self.tmpl_body.insert("1.0", DEFAULT_TEMPLATES["Email"]["body"])

    def _animate_tab_wipe(self):
        """Native 60FPS fading transition for tabs to hide layout swapping"""
        self.content._parent_canvas.yview_moveto(0) # reset scroll

    def _on_switch_toggle(self):
        mode = self.type_var.get()
        self.mode_switch.configure(text=f"Mode: {mode}")
        self._on_type_change(mode)

    def _insert_variable(self, code):
        self.tmpl_body.insert("insert", code)
        self.tmpl_body.focus_set()

    def _on_type_change(self, val):
        if val == "Sequence":
            self.tmpl_frame.pack(fill="x", padx=0, pady=0)
            if self.current_mode in ["Outlook", "Gmail"]:
                self.tmpl_subj.pack(fill="x", padx=25, pady=(8, 8))
            else:
                self.tmpl_subj.pack_forget()
        else:
            self.tmpl_frame.pack_forget()

    # ------------------ BUSINESS LOGIC ------------------
    def _browse(self):
        f = filedialog.askopenfilename(filetypes=[("Data Files", "*.csv *.json *.xlsx"), ("All", "*.*")])
        if not f: return
        self.loaded_file_path = f
        self.file_entry.configure(state="normal")
        self.file_entry.delete(0, "end")
        self.file_entry.insert(0, os.path.basename(f))
        self.file_entry.configure(state="disabled")

        if not load_engines():
            self.file_status.configure(text="Error loading engines.", text_color=COLORS["red"])
            return

        cols, data = csv_parser.parse_file(f)
        if cols and data:
            self.detected_columns = cols
            self.loaded_data = data
            self.file_status.configure(text=f"Loaded {len(data)} prospects.", text_color=COLORS["text_primary"])
            self.btn_start.configure(state="normal")
            
            log_msg = f"✅ Extracted Variables:\n"
            for k, v in cols.items():
                if v: log_msg += f"  • [{k}] mapped to '{v}'\n"
            self._log_msg(log_msg)
        else:
            self.file_status.configure(text="Invalid file format.", text_color=COLORS["red"])

    def _login_action(self):
        if not load_engines(): return
        mode = self.current_mode
        self._log_msg(f"Launching {mode} Browser...")
        threading.Thread(target=self._launch_browser_thread, args=(mode,), daemon=True).start()

    def _launch_browser_thread(self, mode):
        try:
            port = LI_PORT if mode == "LinkedIn" else (OL_PORT if mode == "Outlook" else GM_PORT)
            url = "https://www.linkedin.com" if mode == "LinkedIn" else ("https://outlook.office.com" if mode == "Outlook" else "https://mail.google.com")
            profile_name = f"Evernex_{mode}_Profile"
            
            chrome = get_chrome_path()
            if not chrome:
                self.log_q.put(("log", f"❌ Chrome not found on system.", 0, 0))
                return
                
            p_dir = os.path.join(os.path.expanduser("~"), profile_name)
            os.makedirs(p_dir, exist_ok=True)
            subprocess.Popen([chrome, f"--remote-debugging-port={port}", f"--user-data-dir={p_dir}", url])
            
            self.log_q.put(("log", f"✅ {mode} Browser launched on port {port}.", 0, 0))
        except Exception as e:
            self.log_q.put(("log", f"❌ Failed to launch browser: {e}", 0, 0))

    def _start(self):
        if not self.loaded_data: return
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.stop_event.clear()
        self.txt_log.delete("1.0", "end")

        threading.Thread(
            target=hub_worker,
            args=(
                self.current_account,
                self.current_mode,
                self.loaded_data,
                self.loaded_file_path,
                self.log_q,
                self.stop_event,
                self.type_var.get(),
                self.tmpl_subj.get() if hasattr(self, 'tmpl_subj') else "",
                self.tmpl_body.get("1.0", "end-1c") if hasattr(self, 'tmpl_body') else ""
            ),
            daemon=True
        ).start()

    def _stop(self):
        self.stop_event.set()
        self._log_msg("🛑 Stop signal issued. Halting after current item...")

    def _poll_queue(self):
        try:
            while True:
                msg_type, msg_text, i, total = self.log_q.get_nowait()
                if msg_type == "start":
                    self.status_lbl.configure(text=msg_text)
                    self.pb.set(0)
                    self._log_msg(msg_text)
                elif msg_type == "log":
                    self._log_msg(msg_text)
                elif msg_type == "progress":
                    self.status_lbl.configure(text=f"{msg_text} ({i}/{total})")
                    self.pb.set((i / total) if total > 0 else 0)
                elif msg_type in ["done", "stopped", "error"]:
                    if msg_type == "error":
                        self._log_msg(msg_text)
                        self.status_lbl.configure(text="Campaign Error", text_color=COLORS["red"])
                    else:
                        self._log_msg(f"✅ {msg_text}")
                        self.status_lbl.configure(text="Finished", text_color=COLORS["text_primary"])
                        self.pb.set(1.0)
                    self.btn_start.configure(state="normal")
                    self.btn_stop.configure(state="disabled")
                    
                    if acct_mgr and self.current_account:
                        try:
                            updated, _ = acct_mgr.authenticate(self.current_account.username, self.current_account.key)
                            if updated: self.current_account = updated
                        except: pass
        except queue.Empty:
            pass
        self.after(200, self._poll_queue)

    def _log_msg(self, msg):
        self.txt_log.insert("end", f"{msg}\n\n")
        self.txt_log.see("end")

if __name__ == "__main__":
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
    app = OutreachHubV9()
    app.mainloop()
