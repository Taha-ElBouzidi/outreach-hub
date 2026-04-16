"""
gmail_engine.py
---------------
Automates Gmail (Google Workspace) using Selenium.
Uses Port 9224 and high-speed JS injection.
"""

import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

def switch_to_gmail(driver):
    """Finds the Gmail tab."""
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "mail.google.com" in driver.current_url:
            return True
    return False

def click_compose(driver):
    """Clicks the 'Compose' (Nouveau message) button."""
    try:
        # Gmail 'Compose' button often has text 'Compose' or 'Nouveau message'
        btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Compose'] | //div[text()='Nouveau message'] | //div[@role='button' and @sub_type='COMPOSE']"))
        )
        btn.click()
        return True
    except: return False

def set_recipient(driver, email):
    try:
        # Gmail 'To' field
        to_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@people_kit_id='recipient_to'] | //input[@aria-label='To'] | //input[@aria-label='À']"))
        )
        driver.execute_script("arguments[0].value = arguments[1];", to_field, email)
        time.sleep(0.5)
        to_field.send_keys(Keys.ENTER)
        return True
    except: return False

def set_subject(driver, subject_text):
    try:
        subj_field = driver.find_element(By.NAME, "subjectbox")
        subj_field.send_keys(subject_text)
        return True
    except: return False

def set_body(driver, body_html):
    """Injects styled HTML into Gmail's compose area."""
    try:
        # Gmail body is a div with role='textbox'
        body_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='textbox' and @aria-label='Message Body'] | //div[@aria-label='Corps du message']"))
        )
        body_field.click()
        # Gmail handles innerHTML better for styling
        driver.execute_script("arguments[0].innerHTML = arguments[1] + arguments[0].innerHTML;", body_field, body_html)
        return True
    except: return False

def click_send(driver):
    try:
        # Wait for any potential Gmail loading
        time.sleep(1.5)
        # Use Ctrl+Enter for Gmail (very reliable)
        body_field = driver.find_element(By.XPATH, "//div[@role='textbox']")
        body_field.send_keys(Keys.CONTROL + Keys.ENTER)
        return True
    except:
        try:
            # Fallback to Send button
            send_btn = driver.find_element(By.XPATH, "//div[@role='button' and text()='Send'] | //div[text()='Envoyer']")
            send_btn.click()
            return True
        except: return False
