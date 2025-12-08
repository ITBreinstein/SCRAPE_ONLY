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

# Haal credentials op uit .streamlit/secrets.toml
STRIIVE_USER = os.getenv("STRIIVE_USER")
STRIIVE_PASS = os.getenv("STRIIVE_PASS")

# --- HELPER: Chrome driver voor Cloud Run ---
def get_chrome_driver(timeout=15):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # of --headless=new afhankelijk van je Chrome versie
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--remote-debugging-port=9222")  # voorkomt crashes

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(timeout)
    return driver


# --- SCRAPE STRIIVE ---
def scrape_striive():
    driver = get_chrome_driver()
    wait = WebDriverWait(driver, 15)
    try:
        driver.get("https://login.striive.com/")
        time.sleep(2)

        # Inloggen
        driver.find_element(By.ID, "email").send_keys(STRIIVE_USER)
        driver.find_element(By.ID, "password").send_keys(STRIIVE_PASS)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Navigeer naar opdrachten
        opdrachten_link = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@href, '/inbox')]//span[contains(text(), 'Opdrachten')]")
            )
        )
        opdrachten_link.click()

        scroll_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.p-scroller")))
        vacature_links_dict = {}
        repeats = 0
        max_repeats = 5

        # Scroll door alle vacatures heen
        while repeats < max_repeats:
            job_elements = driver.find_elements(By.CSS_SELECTOR, "div.job-request-row")
            new_count = 0
            for div in job_elements:
                try:
                    title = div.find_element(By.CSS_SELECTOR, "[data-testid='listJobRequestTitle']").text.strip()
                    opdrachtgever = div.find_element(By.CSS_SELECTOR, "[data-testid='listClientName']").text.strip()
                    regio_raw = div.find_element(By.CSS_SELECTOR, "[data-testid='listRegionName']").text.strip()
                    link = div.find_element(By.CSS_SELECTOR, "a[data-testid='jobRequestDetailLink']").get_attribute("href")

                    # 🔹 Plaats & Regio netjes splitsen
                    plaats = ""
                    regio = regio_raw
                    if " - " in regio_raw:
                        parts = [x.strip() for x in regio_raw.rsplit(" - ", 1)]
                        if len(parts) == 2:
                            plaats, regio = parts
                        else:
                            plaats = regio_raw.strip()

                    if link not in vacature_links_dict:
                        vacature_links_dict[link] = {
                            "Titel": title,
                            "Opdrachtgever": opdrachtgever,
                            "Plaats": plaats,
                            "Regio": regio,
                            "Link": link,
                            "Email": "",
                            "Beschrijving": "",
                            "Bron": "Striive"
                        }
                        new_count += 1
                except:
                    continue

            # Stoppen als geen nieuwe vacatures meer geladen worden
            repeats = repeats + 1 if new_count == 0 else 0
            driver.execute_script("arguments[0].scrollBy(0, 1000);", scroll_container)
            time.sleep(1.2)

        results = []
        for link, vacature in vacature_links_dict.items():
            try:
                driver.get(link)

                # Beschrijving
                try:
                    desc_elem = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='jobRequestDescription']"))
                    )
                    beschrijving_html = desc_elem.get_attribute("innerHTML").strip()
                    soup = BeautifulSoup(beschrijving_html, "html.parser")
                    beschrijving_tekst = soup.get_text(separator="\n").strip()
                    vacature["Beschrijving"] = beschrijving_tekst
                except:
                    vacature["Beschrijving"] = ""

                # Email
                try:
                    email_elem = driver.find_element(By.CSS_SELECTOR, "a[data-testid='recruiterMail']")
                    mail = email_elem.get_attribute("href").replace("mailto:", "").strip()
                    vacature["Email"] = mail
                except:
                    vacature["Email"] = ""

                results.append(vacature)
            except Exception as e:
                print(f"⚠️ Fout bij laden detailpagina: {link} - {e}")
                continue

        # Zet om naar DataFrame
        df = pd.DataFrame(results)
        return df

    except Exception as e:
        print(f"❌ Fout tijdens scraping Striive: {e}")
        return pd.DataFrame()

    finally:
        driver.quit()
