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

def scrape_werkeninfriesland(with_description=True, categories=True):
    driver = get_chrome_driver()
    driver.get("https://www.werkeninfriesland.nl/vacatures/")
    time.sleep(5)

    all_data = []

    # Optioneel: alle categorieën ophalen
    category_urls = ["https://www.werkeninfriesland.nl/vacatures/"]
    if categories:
        select_el = driver.find_element(By.ID, "dynamic_select")
        options = select_el.find_elements(By.TAG_NAME, "option")
        category_urls = [opt.get_attribute("value") for opt in options if opt.get_attribute("value")]

    for cat_url in category_urls:
        driver.get(cat_url)
        time.sleep(3)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.col-md-9.items a"))
            )
            vac_links = driver.find_elements(By.CSS_SELECTOR, "div.col-md-9.items a")
        except TimeoutException:
            print(f"⚠️ Geen vacatures gevonden voor categorie {cat_url}")
            continue

        for idx in range(len(vac_links)):
            try:
                vac_links = driver.find_elements(By.CSS_SELECTOR, "div.col-md-9.items a")  # opnieuw ophalen
                vac = vac_links[idx]

                titel = vac.text.strip().split("\n")[0]
                link = vac.get_attribute("href")

                beschrijving = ""
                if with_description and link:
                    driver.get(link)
                    try:
                        content_el = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.text.color1"))
                        )
                        beschrijving = content_el.text.strip()
                    except:
                        beschrijving = ""
                    driver.back()
                    time.sleep(1)

                all_data.append({
                    "Titel": titel,
                    "Regio": "Friesland",
                    "Link": link,
                    "Beschrijving": beschrijving,
                    "Bron": "Werkeninfriesland"
                })

            except StaleElementReferenceException:
                print(f"⚠️ Stale element bij vacature {idx+1} op categorie {cat_url}, opnieuw proberen...")
                time.sleep(1)
                continue
            except Exception as e:
                print(f"⚠️ Fout bij vacature {idx+1} op categorie {cat_url}: {e}")
                continue

    driver.quit()
    df = pd.DataFrame(all_data)
    df.drop_duplicates(subset=["Titel", "Link"], inplace=True)
    return df
