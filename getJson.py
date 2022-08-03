#!/usr/bin/env python3

from seleniumwire import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys

try:
    import mde_credentials
except ImportError:
    print("Please provide your MDE credentials in ./mde_credentials.py")
    sys.exit(1)

c = webdriver.Chrome()

c.get('https://disneyworld.co.uk/plans/')

# Do the login
sign_in_iframe = WebDriverWait(c, 30).until(
    EC.presence_of_element_located((By.ID, 'disneyid-iframe'))
)

# If needed, remove the cookie popover, otherwise we can't submit the form (as
# the element is not clickable)
try:
    cookie_popover = c.find_element(By.ID, 'onetrust-consent-sdk')
    c.execute_script('return arguments[0].remove();', cookie_popover)
except e:
    print(e)


c.switch_to.frame(sign_in_iframe)
username = c.find_element(By.XPATH, "//input[@type='email']")
password = c.find_element(By.XPATH, "//input[@type='password']")
sign_in = c.find_element(By.XPATH, "//button[@type='submit']")

username.send_keys(mde_credentials.username)
password.send_keys(mde_credentials.password)
sign_in.click()

c.switch_to.default_content()
# Add an implicit wait for the redirect/login flow to happen
c.implicitly_wait(5)

json = None
while json is None:
    for request in c.requests:
        if request.response:
            if 'wdw-itinerary-api/api/v1/guests' in request.url:
                json = decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))

with open('my_plans.json', 'wb') as f:
    f.write(json)

c.quit()

