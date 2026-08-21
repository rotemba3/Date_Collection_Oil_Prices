"""
Module for setting up Selenium WebDriver for scraping Twitter (X).

Functions:
- setup_web_driver(): Configures and initializes a Selenium WebDriver instance.

"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager as CM
from selenium.webdriver.chrome.options import Options


def setup_web_driver():
    """
    Sets up and initializes a Selenium WebDriver instance for Chrome.

    This version attaches Selenium to an already-running Chrome instance
    that you start manually with remote debugging enabled. That Chrome
    window uses your normal profile and login state.

    Flow:
    1. Start Chrome manually with a debug port, e.g. on macOS:

       /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \
           --remote-debugging-port=9222 \
           --user-data-dir=\"$HOME/chrome-selenium-profile\"

    2. Log in to X in that Chrome window.
    3. Run `python main.py` – Selenium will attach to that window and
       start navigating/searching without creating a new profile.

    Returns:
    - webdriver.Chrome: A Selenium WebDriver instance with Chrome configuration.
    """
    chrome_options = Options()
    # Attach to the Chrome instance you started with --remote-debugging-port=9222
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    service = Service(executable_path=CM().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver
