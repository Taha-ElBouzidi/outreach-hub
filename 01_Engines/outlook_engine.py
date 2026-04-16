"""
outlook_engine.py
-----------------
Automates Outlook Web (OWA) using Selenium.
ULTIMATE RESILIENCE: Includes Signature Verification and Dialog Slaying.
"""

import json
import os
import time
import random
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

SIGNATURE_MARKER = "telbouzidi@evernex.com" # Unique text to verify signature load

def get_driver(port=9223):
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def get_chrome_path():
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe")
    ]
    for p in paths:
        if os.path.exists(p): return p
    return None

def ensure_chrome_open(port, url, profile_name):
    """Checks if chrome is open on the port, launches it if not."""
    try:
        # Try to connect to see if it's already open
        get_driver(port=port)
        print(f"[OK] Chrome already open on Port {port}")
    except:
        print(f"[!] Port {port} not found. Launching Chrome Debug Mode...")
        chrome = get_chrome_path()
        if not chrome:
            print("[ERROR] Chrome executable not found!")
            return False
        
        p_dir = os.path.join(os.path.expanduser("~"), profile_name)
        os.makedirs(p_dir, exist_ok=True)
        
        # Launch Chrome
        subprocess.Popen([chrome, f"--remote-debugging-port={port}", f"--user-data-dir={p_dir}", url])
        print("-> Chrome launched. Waiting 8s for load...")
        time.sleep(8)
    return True

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def switch_to_outlook(driver):
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "outlook" in driver.current_url.lower(): return True
    return False

def apply_evernex_styling(text):
    """Bolds key terms, converts newlines to <br>, and wraps in Calibri 10pt."""
    terms = ["Evernex", "Global TPM Provider", "onsite NIST 800-compliant data shredding", 
             "100% WEEE-certified recycling", "Buy-Back program", "NIST 800-compliant shredding",
             "330+ local stocking depots", "ITAD", "Blancco-certified"]
    styled = text.replace("\n", "<br>")
    for t in terms:
        styled = styled.replace(t, f"<b>{t}</b>")
    return f'<div style="font-family: Calibri, sans-serif; font-size: 10pt; color: #000000;">{styled}</div>'

def slay_dialogs(driver):
    """Finds and dismisses ANY blocking dialog/popup."""
    try:
        # Outlook popups always use role='dialog'
        dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog'] | //div[@aria-modal='true']")
        if dialogs:
            for d in dialogs:
                # Look for 'OK', 'Ignorer', 'Dismiss', or 'Continue' buttons inside the dialog
                btns = d.find_elements(By.XPATH, ".//button")
                for b in btns:
                    text = b.text.lower()
                    if any(word in text for word in ["ok", "ignorer", "dismiss", "continue", "envoyer quand même"]):
                        print(f"-> Slaying dialog with button: {b.text}")
                        driver.execute_script("arguments[0].click();", b)
                        return True
    except: pass
    return False

def wait_for_signature(driver, timeout=10):
    """Waits until the signature text is found in the message body."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            body = driver.find_element(By.XPATH, "//div[@aria-label='Message body'] | //div[@aria-label='Corps du message']")
            if SIGNATURE_MARKER in body.text:
                print("[OK] Signature detected.")
                return True
        except: pass
        time.sleep(0.5)
    print("[WARN] Signature not detected within timeout. Proceeding anyway.")
    return False

def click_new_message(driver):
    slay_dialogs(driver) # Clear any leftover popups
    try:
        btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Nouveau message'] | //span[text()='Nouveau message']/ancestor::button"))
        )
        driver.execute_script("arguments[0].click();", btn)
        return True
    except: return False

def set_recipient(driver, email):
    try:
        to_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='To'] | //div[@aria-label='À']"))
        )
        to_field.click()
        driver.execute_script("arguments[0].innerText = arguments[1];", to_field, email)
        time.sleep(1)
        to_field.send_keys(Keys.ENTER)
        return True
    except: return False

def set_subject(driver, subject_text):
    try:
        subject_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Add a subject'] | //input[@placeholder='Ajouter un objet']"))
        )
        subject_field.send_keys(subject_text)
        return True
    except: return False

def set_body(driver, body_html):
    try:
        body_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Message body'] | //div[@aria-label='Corps du message']"))
        )
        body_field.click()
        body_field.send_keys(Keys.CONTROL + Keys.HOME)
        driver.execute_script("arguments[0].insertAdjacentHTML('afterbegin', arguments[1]);", body_field, body_html)
        return True
    except: return False

def click_send(driver):
    try:
        # 1. Wait for signature to appear in DOM
        wait_for_signature(driver)
        
        # 2. Extra safety pause
        time.sleep(1)
        
        # 3. Find Send Button
        wait = WebDriverWait(driver, 10)
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Envoyer'] | //button[contains(., 'Envoyer')] | //button[@data-automation-id='splitbutton-primary']")))
        
        # 4. Attempt Keyboard Send first (often bypasses loading popups)
        print("-> Attempting Keyboard Send (Ctrl+Enter)...")
        body_field = driver.find_element(By.XPATH, "//div[@aria-label='Message body'] | //div[@aria-label='Corps du message']")
        body_field.send_keys(Keys.CONTROL + Keys.ENTER)
        
        # 5. Monitor for Popup and Slay it
        time.sleep(1.5)
        if slay_dialogs(driver):
            print("-> Loading warning dismissed. Retrying send...")
            driver.execute_script("arguments[0].click();", btn)
            
        return True
    except: return False
