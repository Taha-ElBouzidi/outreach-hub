"""
link.py
-------
Universal LinkedIn outreach runner (Sync with GUI Hub).
RESTORED: High-speed direct connection via vanityName.
"""

import json
import os
import re
import sys
import time
import random

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CHROME_PORT = 9222
MAX_NOTE    = 300 

def get_driver():
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_PORT}")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ---------------------------------------------------------------------------
# DIRECT STEPS (RESTORED)
# ---------------------------------------------------------------------------

def connect_direct(driver, profile_url):
    """Jumps directly to the connection box using vanity name."""
    try:
        vanity = profile_url.rstrip("/").split("/in/")[-1]
        invite_url = f"https://www.linkedin.com/preload/custom-invite/?vanityName={vanity}"
        print(f"  -> Jumping to invite: {invite_url}")
        driver.get(invite_url)
        time.sleep(3)
        return True
    except Exception as e:
        print(f"  [FAIL] Could not parse vanity name: {e}")
        return False

def click_add_note(driver):
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Add a note']"))
        )
        driver.execute_script("arguments[0].click();", btn)
        return True
    except Exception:
        return False

def type_message(driver, text):
    try:
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "custom-message"))
        )
        textarea.clear()
        textarea.send_keys(text)
        time.sleep(1)
        return True
    except Exception:
        return False

def click_send(driver):
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send invitation'] | //button[contains(., 'Send')]"))
        )
        driver.execute_script("arguments[0].click();", btn)
        return True
    except: return False

# ---------------------------------------------------------------------------
# MODULAR ENGINE
# ---------------------------------------------------------------------------

def process_one(driver, prospect):
    try:
        url = prospect["linkedin_url"]
        msg = clean_message(prospect.get("final_outreach", ""))
        
        # Original High-Speed Method
        if not connect_direct(driver, url):
            return "failed_vanity_parsing"
        
        if not click_add_note(driver):
            return "failed_no_add_note"
            
        if not type_message(driver, msg):
            return "failed_no_textarea"
            
        if not click_send(driver):
            return "failed_no_send"
            
        return "sent"
    except Exception as e:
        return f"error: {str(e)}"

def clean_message(raw):
    msg = re.sub(r"\n\*\(\d+ chars\)\*$", "", raw).strip()
    return msg[:MAX_NOTE]

def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
