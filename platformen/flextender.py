import time
import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Haal credentials op
FLEX_USER = os.getenv("FLEX_USER")
FLEX_PASS = os.getenv("FLEX_PASS")

# --- HELPER: Chrome driver voor Cloud Run ---
def get_chrome_driver(timeout=15):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")

    driver = webdriver.Chrome(options=chrome_options)  # Selenium Manager regelt driver
    driver.implicitly_wait(timeout)
    return driver


# --- HELPER: totaal aantal pagina's bij Flextender ---
def get_total_pages(driver, wait):
    max_page = 1
    seen_pages = set()
    while True:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.js-wd-paginatorbutton")))
        paginator_buttons = driver.find_elements(By.CSS_SELECTOR, "span.js-wd-paginatorbutton")

        for btn in paginator_buttons:
            text = btn.text.strip()
            if text.isdigit():
                p = int(text)
                seen_pages.add(p)
                if p > max_page:
                    max_page = p

        next_button = next((btn for btn in paginator_buttons if btn.text.strip() == "»"), None)
        if not next_button:
            break

        try:
            next_button.click()
            time.sleep(2)
        except Exception:
            break

        new_pages = {int(btn.text.strip()) for btn in driver.find_elements(By.CSS_SELECTOR, "span.js-wd-paginatorbutton") if btn.text.strip().isdigit()}
        if new_pages.issubset(seen_pages):
            break

    return max_page


def scrape_flextender():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = get_chrome_driver()
    wait = WebDriverWait(driver, 10)

    driver.get("https://app.flextender.nl/")
    time.sleep(2)
    try:
        driver.find_element(By.NAME, "login[username]").send_keys(FLEX_USER)
        driver.find_element(By.NAME, "login[password]").send_keys(FLEX_PASS, Keys.ENTER)
    except Exception:
        print("❌ Inloggen mislukt op Flextender. Check credentials of browserconfig.")

    time.sleep(5)
    driver.get("https://app.flextender.nl/supplier/jobs/recommended")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.css-jobsummarywidget")))
    time.sleep(3)

    total_pages = get_total_pages(driver, wait)

    try:
        paginator = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "span.target-jobsearchresults-page-1")
        ))
        paginator.click()
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Kon niet terug naar pagina 1: {e}")

    data = []

    for page_num in range(1, total_pages + 1):
        try:
            paginator = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, f"span.target-jobsearchresults-page-{page_num}")
            ))
            paginator.click()
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Kan pagina {page_num} niet openen: {e}")
            continue

        try:
            page_divs = wait.until(EC.presence_of_all_elements_located((
                By.CSS_SELECTOR, f"div.css-jobsummarywidget.target-jobsearchresults-page-{page_num}"
            )))
        except Exception as e:
            print(f"❌ Geen vacatures gevonden op pagina {page_num}: {e}")
            continue

        for div in page_divs:
            try:
                card = div.find_element(By.CSS_SELECTOR, ".js-widget-content")
                link_elem = card.find_element(By.CSS_SELECTOR, "a.job-summary-clickable")
                link = link_elem.get_attribute("href")

                titel = card.find_element(By.CSS_SELECTOR, ".flx-jobsummary-title div").text.strip()
                opdrachtgever = card.find_element(By.CSS_SELECTOR, ".flx-jobsummary-client").text.strip()

                vacature = {
                    "pagina": page_num,
                    "Titel": titel,
                    "Opdrachtgever": opdrachtgever,
                    "Link": link,
                    "Plaats": "",
                    "Email": "",
                    "Beschrijving": "",
                    "Bron": "Flextender"
                }

                # Captionvelden uitlezen (voor locatie)
                caption_fields = card.find_elements(By.CSS_SELECTOR, ".caption-field")
                for field in caption_fields:
                    try:
                        label = field.find_element(By.CSS_SELECTOR, ".caption").text.strip()
                        value = field.find_element(By.CSS_SELECTOR, ".field").text.strip()
                        vacature[label] = value
                        if "plaats" in label.lower() or "locatie" in label.lower():
                            vacature["Plaats"] = value
                    except:
                        continue

                # Detailpagina openen in nieuw tabblad
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[1])
                driver.get(link)

                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.css-formattedjobdescription")))
                    desc_html = driver.find_element(By.CSS_SELECTOR, "div.css-formattedjobdescription").get_attribute("innerHTML")
                    vacature["Beschrijving"] = desc_html
                except:
                    vacature["Beschrijving"] = "Geen beschrijving gevonden"

                # E-mailadres vinden
                try:
                    mail_elem = driver.find_element(By.CSS_SELECTOR, "a[href^='mailto:']")
                    vacature["Email"] = mail_elem.get_attribute("href").replace("mailto:", "").strip()
                except:
                    vacature["Email"] = ""

                # Plaats uit detailpagina fallback
                if not vacature["Plaats"]:
                    try:
                        plaats_el = driver.find_element(By.CSS_SELECTOR, ".css-joblocation")
                        vacature["Plaats"] = plaats_el.text.strip()
                    except:
                        pass

                driver.close()
                driver.switch_to.window(driver.window_handles[0])

                data.append(vacature)

            except Exception as e:
                print(f"⚠️ Fout bij vacature verwerken: {e}")
                continue

    driver.quit()
    return pd.DataFrame(data)
