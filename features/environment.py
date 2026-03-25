"""
Environment setup for BDD tests using Behave and Selenium
"""

import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")


def before_all(context):
    """Set up Selenium WebDriver with headless Chromium before all tests"""
    context.base_url = BASE_URL
    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    service = Service(executable_path="/usr/bin/chromedriver")
    context.driver = webdriver.Chrome(service=service, options=options)
    context.driver.implicitly_wait(10)


def after_all(context):
    """Quit the WebDriver after all tests"""
    context.driver.quit()
