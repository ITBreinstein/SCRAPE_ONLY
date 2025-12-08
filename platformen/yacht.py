import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

import time
import numpy as np

import re
import requests

def get_chrome_driver(timeout=15):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--remote-debugging-port=9222")  # voorkomt crashes

    driver = webdriver.Chrome(options=chrome_options)  # Selenium Manager regelt driver
    driver.implicitly_wait(timeout)
    return driver

def scrape_yacht():
    base_url = "https://www.yacht.nl"
    start_url = "https://www.yacht.nl/vacatures?urenperweek=33%20-%2036%20uur&urenperweek=37%20-%2040%2B%20uur&werkervaring=minder%20dan%201%20jaar&werkervaring=1%20-%202%20jaar&werkervaring=2%20-%205%20jaar"

    # === Setup Selenium driver ===
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(start_url)
        time.sleep(3)

        # Klik alle 'Laad meer resultaten' knoppen
        while True:
            try:
                load_more = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.button__load-more")))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more)
                time.sleep(1)
        
                # klik via JS, stabieler
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(3)
        
            except TimeoutException:
                break
            except Exception as e:
                print(f"⚠️ Klikprobleem: {e}")
                break


        # HTML parsen met BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select("a.search-card--vacancy")

        vacatures = []
        for card in cards:
            try:
                link = base_url + card.get("href")
                titel = card.select_one("h4").get_text(strip=True) if card.select_one("h4") else ""
                bedrijf = card.select_one("p.text--grey").get_text(strip=True) if card.select_one("p.text--grey") else ""

                # Regio (plaats)
                regio_el = card.select_one("li.has-icon span:last-child")
                regio = regio_el.get_text(strip=True) if regio_el else ""

                # Detailpagina ophalen
                beschrijving = ""
                try:
                    detail = requests.get(link)
                    if detail.status_code == 200:
                        dsoup = BeautifulSoup(detail.text, "html.parser")
                        beschrijving_el = dsoup.select_one("article.rich-text--vacancy")
                        beschrijving = beschrijving_el.get_text(separator="\n", strip=True) if beschrijving_el else ""
                except Exception as e:
                    print(f"⚠️ Detailpagina mislukt: {e}")

                vacatures.append({
                    "Titel": titel,
                    "Opdrachtgever": bedrijf,
                    "Regio": regio,
                    "Link": link,
                    "Bron": "Yacht",
                    "Beschrijving": beschrijving
                })

                time.sleep(0.2)

            except Exception as e:
                print(f"⚠️ Fout bij vacaturekaart: {e}")

        df = pd.DataFrame(vacatures)

        # === Mapping: Plaats → Provincie via woonplaatsen.csv ===
        woonplaatsen = pd.read_csv("woonplaatsen.csv", sep=",")
        woonplaatsen["Plaats_clean"] = woonplaatsen["Plaats"].astype(str).str.lower().str.strip()
        woonplaatsen["Provincie_clean"] = woonplaatsen["Provincie"].astype(str).str.strip()

        def get_provincie(regio_text):
            if not isinstance(regio_text, str):
                return regio_text
            regio_text_lower = regio_text.lower()
            for _, row in woonplaatsen.iterrows():
                if row["Plaats_clean"] and row["Plaats_clean"] in regio_text_lower:
                    return row["Provincie_clean"]
            return regio_text  # geen match → hou regio zelf

        df["Regio"] = df["Regio"].apply(get_provincie)

        return df

    finally:
        driver.quit()
