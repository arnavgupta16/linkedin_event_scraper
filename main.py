import time
import json
import csv
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
    time.sleep(5)  # Wait for the page to load
    
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
    time.sleep(5)  # Wait for the page to load

def get_event_links(driver):
    print("Extracting event links...")
    event_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/events/')]")
    links = [link.get_attribute('href') for link in event_links]
    print(f"Found {len(links)} events.")
    return links


def get_event_attendees(driver, event_url):
    print(f"Processing event: {event_url}")
    driver.get(event_url)
    time.sleep(5)  # Wait for the page to load
    
    try:
        # Extract event ID from the URL
        event_id = event_url.split('/')[-2]
        
        # Construct the base attendees search URL
        base_attendees_url = f"https://www.linkedin.com/search/results/people/?eventAttending=%5B%22{event_id}%22%5D&origin=EVENT_PAGE_CANNED_SEARCH"
        
        profile_urls = set()  # Using a set to automatically avoid duplicates
        page = 1
        consecutive_empty_pages = 0
        max_consecutive_empty = 3  # Stop after 3 consecutive empty pages
        profiles_since_last_pause = 0
        
        while True:  # We'll use other conditions to break the loop
            current_url = f"{base_attendees_url}&page={page}"
            print(f"Scraping attendees page {page}")
            driver.get(current_url)
            time.sleep(3)  # Wait for page load

            try:
                # Wait for either results or "no results" message
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "li.reusable-search__result-container, div.search-reusables__no-results-message"
                    ))
                )
                
                # Check if we've hit "no results"
                no_results = driver.find_elements(By.CSS_SELECTOR, "div.search-reusables__no-results-message")
                if no_results:
                    consecutive_empty_pages += 1
                    print(f"No results found on page {page}")
                    if consecutive_empty_pages >= max_consecutive_empty:
                        print(f"No results found for {max_consecutive_empty} consecutive pages. Ending search.")
                        break
                    page += 1
                    continue

                # Reset empty pages counter if we found results
                consecutive_empty_pages = 0
                
                # Extract profile URLs
                profile_elements = driver.find_elements(By.CSS_SELECTOR, "a.app-aware-link")
                new_urls = 0
                for element in profile_elements:
                    profile_url = element.get_attribute('href')
                    if profile_url and '/in/' in profile_url:
                        clean_url = profile_url.split('?')[0]  # Remove query parameters
                        if clean_url not in profile_urls:
                            profile_urls.add(clean_url)
                            new_urls += 1
                            profiles_since_last_pause += 1
                
                print(f"Found {new_urls} new profile URLs on page {page}")
                print(f"Total unique profile URLs so far: {len(profile_urls)}")
                
                # Check if we need to pause
                if profiles_since_last_pause >= 100:
                    pause_duration = random.randint(180, 240)  # 3-4 minutes in seconds
                    print(f"Extracted {profiles_since_last_pause} profiles. Pausing for {pause_duration} seconds...")
                    time.sleep(pause_duration)
                    profiles_since_last_pause = 0
                    print("Resuming extraction...")
                
                # If we didn't find any new URLs on this page, increment empty counter
                if new_urls == 0:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_consecutive_empty:
                        print(f"No new URLs found for {max_consecutive_empty} consecutive pages. Ending search.")
                        break
                
                page += 1
                
            except TimeoutException:
                print(f"Timeout on page {page}. Trying next page.")
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= max_consecutive_empty:
                    print(f"Timeout for {max_consecutive_empty} consecutive pages. Ending search.")
                    break
                page += 1
                continue

    except Exception as e:
        print(f"Error getting attendees: {str(e)}")
    
    print(f"Finished processing event. Total unique profile URLs: {len(profile_urls)}")
    return list(profile_urls)

def load_history(history_file):
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            return json.load(f)
    return {"events": [], "profiles": []}

def save_history(history, history_file):
    with open(history_file, 'w') as f:
        json.dump(history, f)

def update_csv_output(history, csv_file):
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Profile URL'])
        for url in history['profiles']:
            writer.writerow([url])


def main():
    cookies_file = 'linkedin_cookies.json'
    history_file = 'linkedin_scraping_history.json'
    csv_output_file = 'linkedin_profile_urls.csv'
    log_file = 'scraping_log.txt'
    
    options = webdriver.ChromeOptions()
    options.add_argument("user-data-dir=selenium")  # This will store the session data
    driver = webdriver.Chrome(options=options)
    
    history = load_history(history_file)
    failed_events = []
    
    try:
        login_to_linkedin(driver, cookies_file)
        
        # Navigate to the events page
        navigate_to_events_page(driver)
        
        event_links = get_event_links(driver)
        
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"\nScraping session started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"Found {len(event_links)} events to process\n")
        
        for i, event_url in enumerate(event_links, 1):
            if event_url in history["events"]:
                print(f"Skipping already processed event: {event_url}")
                continue
            
            print(f"\nProcessing event {i}/{len(event_links)}: {event_url}")
            try:
                profile_urls = get_event_attendees(driver, event_url)
                
                new_profiles = 0
                for url in profile_urls:
                    if url not in history["profiles"]:
                        history["profiles"].append(url)
                        new_profiles += 1
                
                if new_profiles > 0:
                    print(f"Added {new_profiles} new profile URLs from this event.")
                    save_history(history, history_file)
                    update_csv_output(history, csv_output_file)
                else:
                    print("No new profile URLs added from this event.")
                
                history["events"].append(event_url)
                save_history(history, history_file)  # Save after each event
                
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"Successfully processed event: {event_url}\n")
                    log.write(f"Added {new_profiles} new profile URLs\n")
                    log.write(f"Total unique profiles so far: {len(history['profiles'])}\n")
            
            except Exception as e:
                print(f"Error processing event {event_url}: {str(e)}")
                failed_events.append(event_url)
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"Failed to process event: {event_url}\n")
                    log.write(f"Error: {str(e)}\n")
                continue
            
            # Optional: Add a pause every few events to avoid rate limiting
            if i % 5 == 0:
                print("\nTaking a short break...")
                time.sleep(30)  # 30 second break every 5 events
        
        # Retry failed events
        if failed_events:
            print("\nRetrying failed events...")
            for event_url in failed_events[:]:  # Use a slice copy to safely remove items
                try:
                    profile_urls = get_event_attendees(driver, event_url)
                    
                    new_profiles = 0
                    for url in profile_urls:
                        if url not in history["profiles"]:
                            history["profiles"].append(url)
                            new_profiles += 1
                    
                    if new_profiles > 0:
                        save_history(history, history_file)
                        update_csv_output(history, csv_output_file)
                    
                    history["events"].append(event_url)
                    failed_events.remove(event_url)
                    
                    with open(log_file, 'a', encoding='utf-8') as log:
                        log.write(f"Successfully processed event on retry: {event_url}\n")
                        log.write(f"Added {new_profiles} new profile URLs\n")
                
                except Exception as e:
                    print(f"Failed to process event {event_url} on retry: {str(e)}")
                    with open(log_file, 'a', encoding='utf-8') as log:
                        log.write(f"Failed to process event on retry: {event_url}\n")
                        log.write(f"Error: {str(e)}\n")
        
        # Final report
        if failed_events:
            print("\nThe following events could not be processed:")
            for event_url in failed_events:
                print(event_url)
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write("\nEvents that could not be processed:\n")
                for event_url in failed_events:
                    log.write(f"{event_url}\n")
        
        print(f"\nScraping completed!")
        print(f"Total unique profile URLs collected: {len(history['profiles'])}")
        print(f"Total events processed: {len(history['events'])}")
        print(f"Failed events: {len(failed_events)}")
        
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"\nScraping session ended at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"Total unique profile URLs: {len(history['profiles'])}\n")
            log.write(f"Total events processed: {len(history['events'])}\n")
            log.write(f"Failed events: {len(failed_events)}\n")
    
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"\nAn unexpected error occurred: {str(e)}\n")
    
    finally:
        driver.quit()

def load_history(history_file):
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"events": [], "profiles": []}

def save_history(history, history_file):
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f)

def update_csv_output(history, csv_file):
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Profile URL'])
        for url in history['profiles']:
            writer.writerow([url])

if __name__ == "__main__":
    main()
