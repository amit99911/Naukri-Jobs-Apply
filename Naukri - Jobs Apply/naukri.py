#! python3
# -*- coding: utf-8 -*-
"""Naukri Unlimited Batch Applicant - Apply 5, Pause, Repeat"""

import io
import logging
import os
import sys
import time
from datetime import datetime
from random import choice, randint, uniform
from string import ascii_uppercase, digits
import schedule

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    ElementClickInterceptedException,
    StaleElementReferenceException
)

# Imports for Chrome
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions

# Imports for Edge
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import constants

# --- CONFIGURATION ---
originalResumePath = constants.ORIGINAL_RESUME_PATH
modifiedResumePath = constants.MODIFIED_RESUME_PATH
username = constants.USERNAME
password = constants.PASSWORD
mob = constants.MOBILE
NaukriURL = constants.NAUKRI_LOGIN_URL

# Script Settings
updatePDF = False  # Set True to update resume timestamp periodically
headless = False   # Set True to run without browser window

# Logging Setup
logging.basicConfig(level=logging.INFO, filename="naukri_apply.log", format="%(asctime)s : %(message)s")
os.environ["WDM_LOCAL"] = "1"
os.environ["WDM_LOG_LEVEL"] = "0"

def log_msg(message):
    print(message)
    logging.info(message)

def catch(error):
    _, _, exc_tb = sys.exc_info()
    lineNo = str(exc_tb.tb_lineno)
    msg = "%s : %s at Line %s." % (type(error), error, lineNo)
    print(msg)
    logging.error(msg)

# --- UTILITY FUNCTIONS ---

def is_element_present(driver, by, value):
    try:
        driver.find_element(by=by, value=value)
        return True
    except NoSuchElementException:
        return False

def wait_for_element(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    except TimeoutException:
        return None

def wait_for_clickable(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
    except TimeoutException:
        return None

def randomText():
    return "".join(choice(ascii_uppercase + digits) for _ in range(randint(1, 5)))

# --- BROWSER SETUP ---

def LoadNaukri(headless):
    # Defaulting to Chrome for better stability with this logic
    options = ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popups")
    if headless:
        options.add_argument("--headless=new")
    
    try:
        driver = webdriver.Chrome(options=options, service=ChromeService())
    except Exception as e:
        log_msg(f"Chrome Driver Error: {e}")
        driver = webdriver.Chrome(options=options)
        
    driver.get(NaukriURL)
    return driver

# --- LOGIN & AUTH ---

def naukriLogin(driver):
    log_msg("Attempting Login...")
    try:
        wait = WebDriverWait(driver, 20)
        
        # Check if already logged in
        if is_element_present(driver, By.XPATH, "//div[@class='nI-gNb-drawer__icon']"):
            log_msg("Already Logged In.")
            return True

        # Locate inputs
        user_field = wait_for_element(driver, By.XPATH, "//input[contains(@placeholder, 'Email') or contains(@placeholder, 'Username')]")
        pass_field = wait_for_element(driver, By.XPATH, "//input[contains(@placeholder, 'Password')]")
        
        if user_field and pass_field:
            user_field.clear()
            user_field.send_keys(username)
            pass_field.clear()
            pass_field.send_keys(password)
            
            login_btn = wait_for_clickable(driver, By.XPATH, "//button[@type='submit']")
            if login_btn:
                login_btn.click()
            
            # Wait for dashboard
            if wait_for_element(driver, By.XPATH, "//div[@class='nI-gNb-drawer__icon']", timeout=30):
                log_msg("Login Successful.")
                return True
        
        log_msg("Login Failed.")
        return False
    except Exception as e:
        catch(e)
        return False

# --- JOB APPLICATION LOGIC ---

def handle_apply_modal(driver):
    """
    Handles the modal popup after clicking Apply.
    Returns True if successfully applied, False if skipped due to complex questions.
    """
    try:
        # Check for 'Your application has been sent' immediate success
        success_msg = wait_for_element(driver, By.XPATH, "//*[contains(text(), 'successfully applied') or contains(text(), 'Application sent')]", timeout=3)
        if success_msg:
            return True

        # Check for Chatbot/Modal Layer
        log_msg("Checking for application modal...")
        
        # Look for the 'Submit' or 'Apply' button in the modal
        submit_xpath = "//button[contains(text(), 'Submit') or contains(text(), 'Apply')][not(@disabled)]"
        submit_btn = wait_for_clickable(driver, By.XPATH, submit_xpath, timeout=5)
        
        if submit_btn:
            # Check for mandatory text inputs that are empty (Custom Questions)
            # If there is a required text input visible, we skip because we don't know the answer
            inputs = driver.find_elements(By.XPATH, "//input[@type='text' and @required]")
            for inp in inputs:
                if inp.is_displayed() and inp.get_attribute("value") == "":
                    log_msg("   -> Skipped: Job asks for custom text input.")
                    return False

            submit_btn.click()
            time.sleep(2)
            return True
        else:
            # If no submit button found, it might be a complex form or external redirect
            log_msg("   -> Skipped: No simple submit button found in modal.")
            return False

    except Exception as e:
        log_msg(f"   -> Error in modal handling: {e}")
        return False
    finally:
        # Close any lingering modals if we failed
        try:
            close_btn = driver.find_element(By.XPATH, "//*[contains(@class, 'crossIcon')]")
            if close_btn.is_displayed():
                close_btn.click()
        except:
            pass

def apply_to_jobs_batch(driver, batch_size=5):
    """
    Applies to jobs in recommended section.
    Returns number of jobs applied.
    """
    count = 0
    driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
    time.sleep(5)
    
    log_msg("Scanning Recommended Jobs...")
    
    # Get all job links first to avoid stale elements
    job_links = []
    try:
        # Targeting the Job Title Link
        elements = driver.find_elements(By.XPATH, "//a[contains(@class, 'title')]")
        for el in elements:
            url = el.get_attribute("href")
            if url and url not in job_links:
                job_links.append(url)
    except Exception as e:
        catch(e)
        return 0

    log_msg(f"Found {len(job_links)} potential jobs.")
    
    # Store main window handle
    main_window = driver.current_window_handle

    for url in job_links:
        if count >= batch_size:
            break
            
        try:
            log_msg(f"Processing Job {count + 1}/{batch_size}...")
            
            # Open job in new tab
            driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(2)
            driver.switch_to.window(driver.window_handles[-1])
            
            # 1. Check if already applied
            if is_element_present(driver, By.XPATH, "//*[contains(text(), 'Applied')]"):
                log_msg("   -> Already Applied. Skipping.")
                driver.close()
                driver.switch_to.window(main_window)
                continue

            # 2. Find Apply Button
            apply_btn = wait_for_clickable(driver, By.XPATH, "//button[contains(text(), 'Apply')]", timeout=5)
            
            if apply_btn:
                # Check if it is "Apply on Company Website" (External)
                if "company" in apply_btn.text.lower():
                    log_msg("   -> Skipped: External Company Site.")
                else:
                    apply_btn.click()
                    time.sleep(2)
                    
                    # Handle the application logic
                    if handle_apply_modal(driver):
                        log_msg("   -> SUCCESS: Applied.")
                        count += 1
                    else:
                        log_msg("   -> Failed/Skipped.")
            else:
                log_msg("   -> Apply button not found.")

            # Close tab
            driver.close()
            driver.switch_to.window(main_window)
            time.sleep(randint(2, 5)) # Human-like pause between jobs

        except Exception as e:
            catch(e)
            # Ensure we get back to main window if error
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(main_window)

    return count

# --- MAIN LOOP ---

def main():
    log_msg("----- Naukri Automation Started -----")
    driver = LoadNaukri(headless)
    
    try:
        if not naukriLogin(driver):
            log_msg("Login failed. Exiting.")
            driver.quit()
            return

        total_applied = 0
        
        while True:
            log_msg(f"\n--- Starting Batch (Total Applied so far: {total_applied}) ---")
            
            # Run a batch of 5
            applied_in_batch = apply_to_jobs_batch(driver, batch_size=5)
            total_applied += applied_in_batch

                        # Choose job source: 'recommended' or 'inbox'
            job_source = 'inbox'  # Change to 'recommended' for recommended jobs
            
            if job_source.lower() == 'inbox':
                applied_in_batch = apply_to_inbox_jobs(driver, batch_size=5)
            else:
                applied_in_batch = apply_to_jobs_batch(driver, batch_size=5)
            
            if applied_in_batch == 0:
                log_msg("No relevant jobs found in this pass. Sleeping for 5 mins before refresh...")
                time.sleep(300)
            else:
                # Batch finished, sleep randomly
                sleep_time = randint(120, 300) # 2 to 5 minutes
                log_msg(f"Batch Complete. Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)

            # Optional: Update Resume every 20 applications to keep profile fresh
            if updatePDF and total_applied > 0 and total_applied % 20 == 0:
                log_msg("Updating Resume timestamp...")
                # Call existing update functions here (UpdateResume/UploadResume) - omitted for brevity in loop
                
    except KeyboardInterrupt:
        log_msg("Stopped by User.")
    except Exception as e:
        catch(e)
    finally:
        if driver:
            driver.quit()
        log_msg("----- Script Ended -----")


# --- INBOX JOBS APPLICATION LOGIC ---
def apply_to_inbox_jobs(driver, batch_size=5):
    """
    Applies to jobs from inbox (NVites).
    Returns number of jobs applied.
    """
    count = 0
    driver.get("https://www.naukri.com/mnjuser/inbox")
    time.sleep(5)
    
    log_msg("Scanning Inbox (NVites) Jobs...")
    
    # Get all apply buttons first
    apply_buttons = []
    try:
        # Find all job items in the inbox
        job_items = driver.find_elements(By.XPATH, "//div[contains(@id, 'nvite-item') or contains(@class, 'nvite')]")
        log_msg(f"Found {len(job_items)} jobs in inbox.")
        
        # For each job item, check if there's an Apply button
        for idx, item in enumerate(job_items):
            if count >= batch_size:
                break
            
            try:
                log_msg(f"Processing Inbox Job {count + 1}/{batch_size}...")
                
                # Find apply button within this job item
                apply_btn = item.find_element(By.XPATH, ".//button[contains(text(), 'Apply')]")
                
                # Check if already applied
                if "Not interested" in item.text or "Applied" in item.text:
                    log_msg(" -> Already Applied or Not Interested. Skipping.")
                    continue
                
                if apply_btn and apply_btn.is_displayed():
                    apply_btn.click()
                    time.sleep(2)
                    
                    # Handle the application modal
                    if handle_apply_modal(driver):
                        log_msg(" -> SUCCESS: Applied via Inbox.")
                        count += 1
                    else:
                        log_msg(" -> Failed/Skipped.")
                        
                    time.sleep(randint(2, 5))  # Human-like pause
            except Exception as e:
                log_msg(f" -> Error processing job: {e}")
                continue
                
    except Exception as e:
        catch(e)
        return count
    
    return count



if __name__ == "__main__":

    main()
