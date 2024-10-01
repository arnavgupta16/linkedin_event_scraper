# LinkedIn Event Attendees Scraper

This Python script automatically scrapes profile URLs of attendees from LinkedIn events you've attended or are planning to attend. It handles authentication, maintains a history of processed events, and saves unique profile URLs to avoid duplicates.

## Features

- Automated login with support for 2FA
- Scrapes all pages of attendees for each event
- Maintains history to avoid re-processing events
- Saves unique profile URLs to CSV
- Detailed logging for debugging
- Handles rate limiting with automatic pauses

## Requirements

- Python 3.7 or higher
- Chrome browser installed
- Chrome WebDriver matching your Chrome version

## Installation

1. Clone the repository:
```bash
git clone https://github.com/arnavgupta16/linkedin_event_scraper
cd linkedin_event_scraper
```

2. Create a virtual environment (recommended):
```bash
python -m venv env
source env/bin/activate  # On Windows, use: env\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Make sure you have the correct ChromeDriver installed and in your PATH

2. Run the script:
```bash
python main.py
```

3. When prompted, log in to LinkedIn:
   - Enter your email and password
   - Complete 2FA if required
   - The script will save cookies for future use

## Output

The script generates several files:
- `linkedin_profile_urls.csv`: Contains all unique profile URLs
- `linkedin_scraping_history.json`: Maintains history of processed events and URLs
- `scraping_log.txt`: Detailed log of the scraping process
- `linkedin_cookies.json`: Saved cookies for future sessions

## Notes

- The script respects LinkedIn's structure and includes delays to avoid being blocked
- It's recommended to run the script during off-peak hours
- The script may take several hours to complete if you have many events
- LinkedIn may occasionally present CAPTCHAs which require manual intervention

## Troubleshooting

1. If you encounter login issues:
   - Delete the `linkedin_cookies.json` file to force a new login

2. If the script stops prematurely:
   - The history file ensures you can resume where you left off
   - Just run the script again

## Legal Disclaimer

This tool is for educational purposes only. Use of this tool must comply with LinkedIn's terms of service and robots.txt file. The user assumes all responsibility for the use of this tool.
