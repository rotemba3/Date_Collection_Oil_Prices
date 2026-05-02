# Twitter Scraper

A Python-based scraper for extracting data from Twitter (X) using Selenium WebDriver. The scraper supports three main functionalities: scraping tweets based on hashtags, user timelines, and user followers/following data.

## Features

- **Hashtag Scraping (`side=0`)**
  - Scrape tweets associated with specific hashtags within a date range.
  
- **User Timeline Scraping (`side=1`)**
  - Scrape tweets from the timelines of specific users within a date range.
  
- **Followers/Following Scraping (`side=3`)**
  - Scrape the followers, following, and verified followers of specific users.

## Prerequisites

1. **Python 3.8+**
   - Ensure Python is installed on your system.
   
2. **Selenium**
   - Install the Selenium library for Python:
     ```bash
     pip install selenium
     ```

3. **WebDriver Manager**
   - Use WebDriver Manager to manage the ChromeDriver:
     ```bash
     pip install webdriver-manager
     ```

4. **Pandas**
   - Install Pandas for data manipulation:
     ```bash
     pip install pandas
     ```

5. **Google Chrome**
   - Ensure Google Chrome is installed on your system.

## Installation

1. **Clone the Repository**
   ```bash
   git@github.com:aviade5/twitter-scraper.git
   cd twitter-scraper

2. **Setup**
   - Place your Twitter credentials in `WebDriverSetup.py` for the login process.
   - Ensure the Selenium WebDriver setup is complete.

## File Overview and Explanation

### `main.py`
- **Purpose**: Serves as the entry point for the scraper, handling different modes (`side` values) for scraping.
- **Key Functions**:
  - `side=0`: Scrapes tweets using hashtags for a given date range.
  - `side=1`: Scrapes tweets from the timelines of specified users.
  - `side=3`: Scrapes followers, following, and verified followers of specified users.
- **Output**: Saves the scraped data as CSV files.

### `SearchScrapper.py`
- **Purpose**: Handles the logic for scraping tweets based on hashtags or user timelines.
- **Key Features**:
  - Uses Selenium WebDriver to navigate Twitter search queries.
  - Extracts tweet data, including text, author, likes, retweets, hashtags, and more.
  - Implements a deduplication mechanism to avoid processing the same tweet multiple times.
- **Output**: Returns a set of unique `Tweet` objects containing all relevant data.

### `SearchScrapperDetails.py`
- **Purpose**: Scrapes the followers and following lists of specific users.
- **Key Features**:
  - Extracts usernames from the followers or following pages.
  - Scrolls through the page dynamically to load more data.
  - Ensures deduplication of user data.
- **Output**: Returns a set of `UserDetail` objects containing usernames.

### `WebDriverSetup.py`
- **Purpose**: Configures and initializes the Selenium WebDriver.
- **Key Features**:
  - Uses `webdriver-manager` to automatically download and manage the ChromeDriver.
  - Handles Twitter login with placeholder credentials.
  - Prepares the WebDriver for scraping tasks.
- **Output**: Returns a ready-to-use Selenium WebDriver instance.

> **Note:** The current setup attaches Selenium to a Chrome window that you start manually with remote debugging enabled, using your normal logged-in X account. You no longer need to put your credentials inside `WebDriverSetup.py`.

## Usage

1. **Run the Program**
   - Open a terminal in the project directory and run:
     ```bash
     python main.py
     ```

2. **Choose a Scraping Mode**
   - Set the `side` parameter in `main.py`:
     - `side=0`: Scrape tweets using hashtags.
     - `side=1`: Scrape tweets from user timelines.
     - `side=3`: Scrape followers/following data for users.

3. **View Results**
   - Results are saved as CSV files in the project directory:
     - Hashtag tweets: `<start_date>_to_<end_date>_hashtag_tweets.csv`
     - User tweets: `<start_date>_to_<end_date>_user_tweets.csv`
     - Followers/Following: `user_follows.csv`

<!-- ============================================================ -->
## Running with your logged-in Chrome session (recommended flow)

To avoid X blocking automated logins, the scraper uses an existing Chrome session that you start manually with remote debugging enabled.

1. **Start a dedicated Chrome window (macOS example)**
   - Close all regular Chrome windows first.
   - In a terminal, run:
     ```bash
     /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
       --remote-debugging-port=9222 \
       --user-data-dir="$HOME/chrome-selenium-profile"
     ```
   - This opens a new Chrome window using a dedicated profile stored in `~/chrome-selenium-profile`.

2. **Log in to X in that window**
   - Go to `https://x.com`.
   - Log in with your account and make sure you can see the home feed and perform searches.
   - Leave this Chrome window **open**.

3. **Run the scraper**
   - In your virtual environment, from the project directory, run:
     ```bash
     python main.py
     ```
   - `WebDriverSetup.py` connects to the Chrome instance via `127.0.0.1:9222` and reuses your logged-in session.
   - Depending on the `side` you configured in `main.py`, the script will open the relevant X search pages in that same window and start scraping.

4. **Check the output**
   - When scraping finishes, CSV files such as `2023-11-25_to_2023-12-02_hashtag_tweets.csv` will appear in the project directory.
   - You can open them with Excel, Google Sheets, or any CSV viewer to inspect the collected data.


<!-- ============================================================ -->
## Example

### Scraping Tweets Using Hashtags
1. Set `side=0` in `main.py`.
2. Specify hashtags, start date, and end date.
3. Run the program to generate a CSV of tweets for the specified hashtags.

### Scraping User Timelines
1. Set `side=1` in `main.py`.
2. Specify usernames, start date, and end date.
3. Run the program to generate a CSV of tweets from the specified user timelines.

### Scraping Followers/Following
1. Set `side=3` in `main.py`.
2. Specify usernames to scrape their followers or following data.
3. Run the program to generate a CSV of the user’s follower/following lists.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Submit a pull request for review.
