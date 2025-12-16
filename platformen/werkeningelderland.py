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

def scrape_werkeningelderland(with_description=True):

    driver = get_chrome_driver()
    driver.set_page_load_timeout(30)

    start_url = "https://www.werkeningelderland.nl/vacatures/?education%5B%5D=hbo&education%5B%5D=wo"
    driver.get(start_url)
    time.sleep(4)

    # -------------------------------------------------
    # 1. Haal ALLE pagina-URLs uit de paginatie
    # -------------------------------------------------
    page_urls = set([start_url])

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "nav.pagination a.pagination__link"))
        )
        links = driver.find_elements(By.CSS_SELECTOR, "nav.pagination a.pagination__link")

        for ln in links:
            href = ln.get_attribute("href")
            if href and "page" in href:
                page_urls.add(href)

    except:
        print("⚠️ Geen paginatie gevonden, alleen pagina 1 beschikbaar.")

    page_urls = sorted(list(page_urls))  # mooi gesorteerd
    print(f"📄 Aantal pagina’s gevonden: {len(page_urls)}")

    # -------------------------------------------------
    # Scrapen per pagina
    # -------------------------------------------------
    all_data = []

    for page_idx, page_url in enumerate(page_urls[:8], start=1):
        print(f"\n➡️ SCRAPING PAGINA {page_idx}: {page_url}")

        driver.get(page_url)
        time.sleep(4)

        # Wacht op vacatures
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "ul.vacancies__listing li.vacancies__item")
                )
            )
            vacatures = driver.find_elements(
                By.CSS_SELECTOR, "ul.vacancies__listing li.vacancies__item"
            )
        except TimeoutException:
            print("⛔ Geen vacatures gevonden op deze pagina.")
            continue

        # -------------------------------------------------
        # Loop door vacatures op deze pagina
        # -------------------------------------------------
        for idx in range(len(vacatures)):
            try:
                vacatures = driver.find_elements(
                    By.CSS_SELECTOR, "ul.vacancies__listing li.vacancies__item"
                )
                vac = vacatures[idx]

                # Titel
                try:
                    titel = vac.find_element(
                        By.CSS_SELECTOR, "h1.vacancy__title"
                    ).text.strip()
                except:
                    titel = ""

                # Opdrachtgever (via logo ALT)
                try:
                    opdrachtgever = vac.find_element(
                        By.CSS_SELECTOR, "aside img.vacancy__sidebar__logo__source"
                    ).get_attribute("alt").replace("Logo ", "").strip()
                except:
                    opdrachtgever = ""

                # Standplaats
                try:
                    plaats = vac.find_element(
                        By.XPATH, ".//li[.//li[contains(text(),'Standplaats')]]/li[2]"
                    ).text.strip()
                except:
                    plaats = ""

                # Link
                try:
                    link = vac.find_element(By.TAG_NAME, "a").get_attribute("href")
                except:
                    link = ""

                # Naar detailpagina
                driver.execute_script("arguments[0].scrollIntoView(true);", vac)
                try:
                    vac.click()
                except:
                    driver.execute_script("arguments[0].click();", vac)
                time.sleep(2)

                # Beschrijving ophalen
                beschrijving = ""
                if with_description:
                    try:
                        content = WebDriverWait(driver, 6).until(
                            EC.presence_of_element_located(
                                (
                                    By.CSS_SELECTOR,
                                    "section.single-vacancy__content section.editor",
                                )
                            )
                        )
                        beschrijving = content.get_attribute("innerText").strip()
                    except:
                        beschrijving = ""

                # Opslaan
                all_data.append(
                    {
                        "Titel": titel,
                        "Opdrachtgever": opdrachtgever,
                        "Email": "",
                        "Plaats": plaats,
                        "Regio": "Gelderland",
                        "Link": link,
                        "Beschrijving": beschrijving,
                        "Bron": "Werkeningelderland",
                    }
                )

                driver.back()
                time.sleep(3)

            except Exception as e:
                print(f"⚠️ Fout bij vacature {idx+1} op pagina {page_idx}: {e}")
                try:
                    driver.back()
                except:
                    pass
                time.sleep(2)
                continue

    driver.quit()
    return pd.DataFrame(all_data)
