import time
import pandas as pd
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import pyarrow.parquet as pq
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException, InvalidSessionIdException, TimeoutException

def get_chrome_driver(timeout=15):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(timeout)
    return driver

def scrape_werkenbijnod():

    driver = get_chrome_driver()
    wait = WebDriverWait(driver, 10)
    url = "https://werkenbijnod.nl/vacatures"
    driver.get(url)
    time.sleep(3)

    # Wacht tot de vacatures geladen zijn
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.single-job")))

    soup = BeautifulSoup(driver.page_source, "html.parser")
    jobs = soup.select("div.single-job")

    data = []

    for job in jobs:
        try:
            # Titel en link
            a_tag = job.select_one("h3 a")
            titel = a_tag.get_text(strip=True)
            link = a_tag["href"]

            # Regio (zoals Groningen of Friesland)
            regio_el = job.select_one("li.location")
            regio = regio_el.get_text(strip=True) if regio_el else ""

            # Opdrachtgever (zoals FUMO of Omgevingsdienst Groningen)
            opdrachtgever_el = job.select_one("ul.locations li")
            opdrachtgever = opdrachtgever_el.get_text(strip=True) if opdrachtgever_el else ""

            # Ga naar detailpagina
            driver.get(link)
            time.sleep(1.5)

            # HTML ophalen en parsen
            detail_html = driver.page_source
            detail_soup = BeautifulSoup(detail_html, "html.parser")

            # Beschrijving samenstellen uit 3 secties: "Wat ga je bij ons doen?", "Wie ben jij?", "Wie zijn wij?"
            beschrijving = ""

            for heading in ["Wat ga je bij ons doen?", "Wie ben jij?", "Wie zijn wij?"]:
                section = detail_soup.find("h2", string=lambda s: s and heading in s)
                if section:
                    # Vind de bijbehorende tekstcontainer
                    text_block = section.find_parent("div", class_="col-md-4").find_next_sibling("div", class_="col-md-8")
                    if text_block:
                        block_text = text_block.get_text(separator="\n", strip=True)
                        beschrijving += f"\n\n{heading}\n{block_text}"

            # Data toevoegen
            data.append({
                "Titel": titel,
                "Opdrachtgever": opdrachtgever,
                "Link": link,
                "Regio": regio,
                "Beschrijving": beschrijving.strip(),
                "Bron": "Werken bij NOD"
            })

        except Exception as e:
            print(f"⚠️ Fout bij verwerken vacature: {e}")
            continue

    driver.quit()
    return pd.DataFrame(data)
