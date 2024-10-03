from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import csv
import os
import random

def load_cookies(driver, cookies_file):
    if os.path.exists(cookies_file):
        with open(cookies_file, 'r') as f:
            cookies = json.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
        return True
    return False

def save_cookies(driver, cookies_file):
    with open(cookies_file, 'w') as f:
        json.dump(driver.get_cookies(), f)

def check_login_status(driver):
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(10)  # Wait for the page to load
    
    # Check if we're redirected to a login page
    if "login" in driver.current_url or "signup" in driver.current_url:
        return False
    
    # Check for elements that are typically present when logged in
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "global-nav"))
        )
        return True
    except TimeoutException:
        return False

def login_to_linkedin(driver, cookies_file):
    print("Checking login status...")
    if check_login_status(driver):
        print("Already logged in. Proceeding with scraping.")
        return

    print("Not logged in. Attempting to log in...")
    if load_cookies(driver, cookies_file):
        driver.get("https://www.linkedin.com/feed/")
        if check_login_status(driver):
            print("Logged in successfully using cookies.")
            return
    
    print("Cookie login failed. Manual login required.")
    while True:
        email = input("Enter your LinkedIn email: ")
        password = input("Enter your LinkedIn password: ")
        
        driver.get("https://www.linkedin.com/login")
        
        driver.find_element(By.ID, "username").send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(40)
        
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "input__phone_verification_pin")))
            print("2FA required. Please enter the code manually.")
            input("Press Enter after entering the 2FA code...")
        except TimeoutException:
            print("No 2FA prompt detected. Continuing...")
        
        if check_login_status(driver):
            print("Login successful. Saving cookies.")
            save_cookies(driver, cookies_file)
            return
        else:
            print("Login failed. Please check your credentials and try again.")
            retry = input("Do you want to retry? (y/n): ").lower()
            if retry != 'y':
                print("Exiting due to login failure.")
                exit(1)

def navigate_to_events_page(driver):
    print("Navigating to events page...")
    driver.get("https://www.linkedin.com/mynetwork/network-manager/events/")
    time.sleep(10)  # Wait for the page to load

def get_event_links(driver):
    print("Extracting event links...")
    
    event_urls = set()  # Changed from dict to set since we don't need names
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_pause_time = 2
    no_new_events_count = 0
    max_no_new_events = 3
    start_time = time.time()
    max_time = 300  # 5 minutes timeout
    
    while True:
        if time.time() - start_time > max_time:
            print(f"Reached maximum time limit of {max_time} seconds")
            break
        
        event_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/events/')]")
        current_events_count = len(event_urls)
        
        for element in event_elements:
            url = element.get_attribute('href')
            if url:
                clean_url = url.split('?')[0]
                event_urls.add(clean_url)
        
        if len(event_urls) > current_events_count:
            print(f"Found {len(event_urls) - current_events_count} new events. Total: {len(event_urls)}")
            no_new_events_count = 0
        else:
            no_new_events_count += 1
            print(f"No new events found. Attempt {no_new_events_count} of {max_no_new_events}")
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if (new_height == last_height and no_new_events_count >= max_no_new_events) or no_new_events_count >= max_no_new_events:
            print("Reached end of events or no new events found after multiple attempts")
            break
        
        last_height = new_height
    
    print(f"Total unique events found: {len(event_urls)}")
    return list(event_urls)

def navigate_to_events_page(driver):
    print("Navigating to events page...")
    driver.get("https://www.linkedin.com/mynetwork/network-manager/events/")
    
    # Wait for the events to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/events/')]"))
        )
    except TimeoutException:
        print("Warning: Timeout waiting for events to load. Proceeding anyway...")
    
    # Additional wait to ensure page is fully loaded
    time.sleep(5)


def get_event_attendees(driver, event_url):
    print(f"Processing event: {event_url}")
    driver.get(event_url)
    time.sleep(5)
    
    try:
        event_id = event_url.split('/')[-2]
        base_attendees_url = f"https://www.linkedin.com/search/results/people/?eventAttending=%5B%22{event_id}%22%5D&origin=EVENT_PAGE_CANNED_SEARCH"
        
        profile_urls = set()
        page = 1
        consecutive_empty_pages = 0
        max_consecutive_empty = 3
        profiles_since_last_pause = 0
        
        while True:
            current_url = f"{base_attendees_url}&page={page}"
            print(f"Scraping attendees page {page}")
            driver.get(current_url)
            time.sleep(3)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "li.reusable-search__result-container, div.search-reusables__no-results-message"
                    ))
                )
                
                no_results = driver.find_elements(By.CSS_SELECTOR, "div.search-reusables__no-results-message")
                if no_results:
                    consecutive_empty_pages += 1
                    print(f"No results found on page {page}")
                    if consecutive_empty_pages >= max_consecutive_empty:
                        break
                    page += 1
                    continue

                consecutive_empty_pages = 0
                
                profile_elements = driver.find_elements(By.CSS_SELECTOR, "a.app-aware-link")
                new_urls = 0
                for element in profile_elements:
                    profile_url = element.get_attribute('href')
                    if profile_url and '/in/' in profile_url:
                        clean_url = profile_url.split('?')[0]
                        if clean_url not in profile_urls:
                            profile_urls.add(clean_url)
                            new_urls += 1
                            profiles_since_last_pause += 1
                
                print(f"Found {new_urls} new profile URLs on page {page}")
                print(f"Total unique profile URLs so far: {len(profile_urls)}")
                
                if profiles_since_last_pause >= 100:
                    pause_duration = random.randint(180, 240)  # 3-4 minutes
                    print(f"Extracted {profiles_since_last_pause} profiles. Pausing for {pause_duration} seconds...")
                    time.sleep(pause_duration)
                    profiles_since_last_pause = 0
                    print("Resuming extraction...")
                
                if new_urls == 0:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_consecutive_empty:
                        break
                
                page += 1
                
            except TimeoutException:
                print(f"Timeout on page {page}. Trying next page.")
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= max_consecutive_empty:
                    break
                page += 1
                continue

    except Exception as e:
        print(f"Error getting attendees: {str(e)}")
    
    print(f"Finished processing event. Total unique profile URLs: {len(profile_urls)}")
    return list(profile_urls)

def load_history(history_file):
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"events": {}}

def save_history(history, history_file):
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f)
def update_csv_output(history, csv_file):
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Event URL', 'Profile URL'])
        for event_url, event_data in history['events'].items():
            for profile_url in event_data['profiles']:
                writer.writerow([event_url, profile_url])



def main():
    cookies_file = 'linkedin_cookies.json'
    history_file = 'linkedin_scraping_history.json'
    csv_output_file = 'linkedin_profile_urls.csv'
    log_file = 'scraping_log.txt'
    
    chrome_driver_path = r"C:\path\to\your\chromedriver.exe"  # Update this path
    
    options = webdriver.ChromeOptions()
    options.add_argument("user-data-dir=selenium")
    #driver = webdriver.Chrome(executable_path=chrome_driver_path, options=options)
    driver = webdriver.Chrome(options=options)
    history = load_history(history_file)
    failed_events = []
    
    try:
        login_to_linkedin(driver, cookies_file)
        navigate_to_events_page(driver)
        
        event_urls = get_event_links(driver)
        
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"\nScraping session started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"Found {len(event_urls)} events to process\n")
        
        for event_url in event_urls:
            if event_url in history["events"]:
                print(f"Skipping already processed event: {event_url}")
                continue
            
            try:
                print(f"Processing event: {event_url}")
                profile_urls = get_event_attendees(driver, event_url)
                
                history["events"][event_url] = {
                    "profiles": profile_urls
                }
                
                save_history(history, history_file)
                update_csv_output(history, csv_output_file)
                
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"Successfully processed event: {event_url}\n")
                    log.write(f"Added {len(profile_urls)} profile URLs\n")
            
            except Exception as e:
                print(f"Error processing event {event_url}: {str(e)}")
                failed_events.append(event_url)
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"Failed to process event: {event_url}\n")
                    log.write(f"Error: {str(e)}\n")
                continue
            
            time.sleep(random.randint(3, 5))
        
        # Final report
        print(f"\nScraping completed!")
        print(f"Total events processed: {len(history['events'])}")
        print(f"Failed events: {len(failed_events)}")
        
        if failed_events:
            print("\nFailed events:")
            for url, name in failed_events:
                print(f"- {name} ({url})")
        
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"\nScraping session ended at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"Total events processed: {len(history['events'])}\n")
            log.write(f"Failed events: {len(failed_events)}\n")
    
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"\nAn unexpected error occurred: {str(e)}\n")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
