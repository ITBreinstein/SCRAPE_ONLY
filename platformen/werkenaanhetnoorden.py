import time
import pandas as pd
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
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

def scrape_werkenaanhetnoorden(with_description=True):
    driver = get_chrome_driver()
    driver.get("https://www.werkenaanhetnoorden.nl/vacatures")
    time.sleep(5)

    data = []

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div#objects a.imagebox"))
        )
        vacatures = driver.find_elements(By.CSS_SELECTOR, "div#objects a.imagebox")
    except TimeoutException:
        print("⚠️ Geen vacatures gevonden op de pagina.")
        driver.quit()
        return pd.DataFrame()

    for idx in range(len(vacatures)):
        try:
            vacatures = driver.find_elements(By.CSS_SELECTOR, "div#objects a.imagebox")
            vac = vacatures[idx]

            titel = vac.find_element(By.CSS_SELECTOR, "h3.imagebox-title").text.strip()
            link = vac.get_attribute("href")
            if not link.startswith("http"):
                link = "https://www.werkenaanhetnoorden.nl" + link

            beschrijving = ""
            if with_description:
                driver.get(link)
                try:
                    beschrijving_el = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.object-detail-wrapper"))
                    )
                    beschrijving = beschrijving_el.text.strip()
                except:
                    beschrijving = ""
                driver.back()
                time.sleep(2)

            data.append({
                "Titel": titel,
                "Regio": "Groningen",
                "Link": link,
                "Beschrijving": beschrijving,
                "Bron": "Werkenaanhetnoorden"
            })

        except Exception as e:
            print(f"⚠️ Fout bij vacature {idx+1}: {e}")
            continue

    driver.quit()

    df = pd.DataFrame(data)
    df.drop_duplicates(subset=["Titel", "Link"], inplace=True)
    return df
