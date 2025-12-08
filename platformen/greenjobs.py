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

def scrape_greenjobs(with_description=True, woonplaatsen_csv="woonplaatsen.csv", max_pages=30):
    driver = get_chrome_driver()
    driver.set_page_load_timeout(30)

    base_url = "https://greenjobs.nl/duurzame-vacatures?in%5Bsegment_ids%5D=14&page=1"
    driver.get(base_url)

    all_data = []
    page = 1
    visited_pages = set()

    while True:
        #print(f"📄 Scrapen van pagina {page}...")

        # Stop bij max_pages
        if page > max_pages:
            #print(f"✅ Maximaal aantal pagina’s ({max_pages}) bereikt, stoppen.")
            break

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".wrapper__job-card"))
            )
        except TimeoutException:
            #print(f"❌ Geen vacatures gevonden op pagina {page}.")
            break

        current_url = driver.current_url
        if current_url in visited_pages:
            #print("⚠️ Pagina al bezocht, stoppen.")
            break
        visited_pages.add(current_url)

        vacatures = driver.find_elements(By.CSS_SELECTOR, ".wrapper__job-card")

        for v in vacatures:
            try:
                titel = v.find_element(By.CSS_SELECTOR, ".job__card--title").text.strip()
            except:
                titel = None

            try:
                regio = v.find_element(By.CSS_SELECTOR, ".job__card--description span.text-neutral-700").text.strip()
            except:
                regio = None

            try:
                link = v.find_element(By.CSS_SELECTOR, ".job__card--title").get_attribute("href")
                if link and link.startswith("/"):
                    link = "https://greenjobs.nl" + link
            except:
                link = None

            beschrijving = None
            if with_description and link:
                try:
                    driver.execute_script(f"window.open('{link}', '_blank');")
                    driver.switch_to.window(driver.window_handles[-1])

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".inline-job__content.with-cookie")
                        )
                    )
                    beschrijving_el = driver.find_element(
                        By.CSS_SELECTOR,
                        ".inline-job__content.with-cookie .card-html-styles__inner"
                    )
                    beschrijving = beschrijving_el.text.strip()
                except:
                    beschrijving = None
                finally:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

            all_data.append({
                "Titel": titel,
                "Regio": regio,
                "Link": link,
                "Beschrijving": beschrijving,
                "Bron": "Greenjobs"
            })

        # 🔄 PAGINATIE
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a.btn-next")
            href = next_button.get_attribute("href")

            if not href or "disabled" in next_button.get_attribute("class"):
                #print("✅ Geen volgende pagina meer, stoppen.")
                break

            driver.get(href)
            page += 1
            time.sleep(2)

        except NoSuchElementException:
            #print("✅ Geen volgende knop gevonden, stoppen.")
            break

    driver.quit()
    df = pd.DataFrame(all_data)

    # 🧹 Dubbele rijen verwijderen
    df = df.drop_duplicates(subset=["Titel", "Link"]).reset_index(drop=True)

    # 📍 Regio → Provincie
    try:
        plaatsen = pd.read_csv(woonplaatsen_csv)
        plaatsen["Plaats"] = plaatsen["Plaats"].str.strip()
        plaatsen["Provincie"] = plaatsen["Provincie"].str.strip()
        df["Regio"] = df["Regio"].str.strip()

        df = df.merge(
            plaatsen[["Plaats", "Provincie"]],
            left_on="Regio",
            right_on="Plaats",
            how="left"
        )
        df["Regio"] = df["Provincie"].fillna("Onbekend")
        df.drop(columns=["Plaats", "Provincie"], inplace=True)
    except Exception as e:
        #print(f"⚠️ Provincie mapping mislukt: {e}")
        df["Regio"] = df["Regio"].fillna("Onbekend")

    #print(f"✅ {len(df)} vacatures gevonden op {page} pagina’s.")
    return df
