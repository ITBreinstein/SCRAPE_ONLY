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

def scrape_noordnederlandwerkt(with_description=True, csv_path="woonplaatsen.csv"):
    driver = get_chrome_driver()
    driver.set_page_load_timeout(30)
    driver.get("https://www.noordnederlandwerkt.nl/vacatures-zoeken")
    time.sleep(5)

    data = []

    try:
        # ✅ Wacht tot vacatures zichtbaar zijn
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul.results.jobs.multicolumn li"))
        )
        vacatures = driver.find_elements(By.CSS_SELECTOR, "ul.results.jobs.multicolumn li")
    except TimeoutException:
        print("⚠️ Geen vacatures gevonden op de pagina.")
        driver.quit()
        return pd.DataFrame()

    for idx, vac in enumerate(vacatures, start=1):
        try:
            titel = vac.find_element(By.CSS_SELECTOR, "h3 a").text.strip()
            plaats = vac.find_element(By.CSS_SELECTOR, "span.with-icon.icon-map-marker").text.strip()
            link = vac.find_element(By.CSS_SELECTOR, "a.button.more").get_attribute("href")

            beschrijving = ""
            if with_description:
                driver.get(link)
                try:
                    omschrijving_el = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//div[@class='container section'][h2[text()='Omschrijving']]")
                        )
                    )
                    beschrijving = omschrijving_el.text.strip()
                except TimeoutException:
                    beschrijving = ""
                driver.back()
                time.sleep(2)

            data.append({
                "Titel": titel,
                "Regio": plaats,  # wordt later vervangen door provincie
                "Link": link,
                "Beschrijving": beschrijving,
                "Bron": "Noordnederlandwerkt"
            })

        except Exception as e:
            print(f"⚠️ Fout bij vacature {idx}: {e}")
            continue

    driver.quit()

    df = pd.DataFrame(data)
    df.drop_duplicates(subset=["Titel", "Link"], inplace=True)

    # --- Plaats → Provincie mapping via woonplaatsen.csv ---
    try:
        mapping = pd.read_csv(csv_path, dtype=str)

        # Neem alleen de eerste plaats bij "Plaats / Alternatief"
        mapping["Plaats"] = mapping["Plaats"].str.split("/").str[0].str.strip().str.lower()

        # Normaliseer provincie, Fryslân → Friesland
        mapping["Provincie"] = mapping["Provincie"].str.replace("Fryslân", "Friesland", regex=False).str.strip()

        # Merge op basis van Plaats
        df["Plaats_lower"] = df["Regio"].str.strip().str.lower()
        df = df.merge(mapping[["Plaats", "Provincie"]], how="left", left_on="Plaats_lower", right_on="Plaats")

        # Gebruik provincie waar mogelijk, anders behoud originele plaatsnaam
        df["Regio"] = df["Provincie"].fillna(df["Regio"])

        df.drop(columns=["Plaats_lower", "Plaats", "Provincie"], inplace=True)
    except Exception as e:
        print(f"⚠️ Kon woonplaatsen.csv niet verwerken: {e}")

    return df
