import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_global_stop_flag(state_module):
    return state_module.GLOBAL_STOP

def human_type(element, text, fast, state_module):
    safe_text = "".join(c for c in text if ord(c) <= 0xFFFF)

    if fast:
        if not get_global_stop_flag(state_module):
            element.send_keys(safe_text)
        return

    for char in safe_text:
        if get_global_stop_flag(state_module):
            return
        element.send_keys(char)
        time.sleep(random.uniform(0.005, 0.02))

def wait_for_page_load(driver, state_module, timeout=60):
    if get_global_stop_flag(state_module):
        return
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        pass

def wait_and_find(driver, xpath, state_module, timeout=60):
    if get_global_stop_flag(state_module):
        raise Exception("Stopped")
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))

def wait_and_click(driver, xpath, state_module, timeout=60):
    if get_global_stop_flag(state_module):
        raise Exception("Stopped")
    element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    element.click()
    return element

def js_click(driver, xpath, state_module, timeout=60):
    element = wait_and_find(driver, xpath, state_module, timeout)
    driver.execute_script("arguments[0].click();", element)
    return element
