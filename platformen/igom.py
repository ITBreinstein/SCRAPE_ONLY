import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

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

def scrape_igom(with_description=True):
    driver = get_chrome_driver()
    driver.get("https://www.igom.nl/vacatures")
    time.sleep(3)

    data = []
    seen_links = set()
    page = 1

    # --- Mapping woonplaats → provincie ---
    woonplaatsen_df = pd.read_csv("woonplaatsen.csv")  # kolommen: 'Gemeente met link naar gemeentelijke website', 'Provincie'
    plaats_to_provincie = dict(zip(
        woonplaatsen_df['Gemeente met link naar gemeentelijke website'].str.lower(),
        woonplaatsen_df['Provincie']
    ))

    while True:
        # Scroll tot alles geladen is
        last_height = driver.execute_script("return document.body.scrollHeight")
        same_count = 0
        while same_count < 3:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                same_count += 1
            else:
                same_count = 0
            last_height = new_height

        vacatures = driver.find_elements(By.TAG_NAME, "app-vacature-item")
        total = len(vacatures)

        for i in range(total):
            vacatures = driver.find_elements(By.TAG_NAME, "app-vacature-item")
            vac = vacatures[i]

            # --- Titel ---
            try:
                title = vac.find_element(By.CSS_SELECTOR, "h3.kaart__titel").text.strip()
            except NoSuchElementException:
                title = ""

            # --- Opdrachtgever, Plaats & Provincie ---
            try:
                opdrachtgever_raw = vac.find_element(By.CSS_SELECTOR, "p.kaart__organisatie").text.strip()
                plaats_raw = opdrachtgever_raw.replace("Gemeente ", "").strip()
                plaats_key = plaats_raw.lower()
                if "limburg" in plaats_key:
                    regio = "Limburg"
                else:
                    regio = plaats_to_provincie.get(plaats_key, "")
            except NoSuchElementException:
                opdrachtgever_raw = ""
                plaats_raw = ""
                regio = ""

            link = ""
            desc = ""
            email = ""

            # --- Detailpagina ---
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", vac)
                vac.click()
                time.sleep(2)

                link = driver.current_url
                if link in seen_links:
                    driver.back()
                    time.sleep(2)
                    continue
                seen_links.add(link)

                if with_description:
                    try:
                        desc = driver.find_element(By.CSS_SELECTOR, "div.cb-text-container").text.strip()
                    except NoSuchElementException:
                        desc = ""

                # --- Email (optioneel) ---
                try:
                    email_el = driver.find_element(By.CSS_SELECTOR, "span.contact-item-email")
                    email = email_el.text.strip()
                except NoSuchElementException:
                    email = ""

                driver.back()
                time.sleep(2)

            except StaleElementReferenceException:
                continue
            except Exception as e:
                print(f"⚠️ Fout bij detailpagina: {e}")
                continue

            data.append({
                "Titel": title,
                "Opdrachtgever": opdrachtgever_raw,
                "Plaats": plaats_raw,
                "Regio": regio,
                "Email": email,
                "Link": link,
                "Beschrijving": desc,
                "Bron": "IGOM"
            })

        # --- Volgende pagina ---
        try:
            try:
                overlay = driver.find_element(By.CSS_SELECTOR, ".login-section")
                driver.execute_script("arguments[0].style.display='none';", overlay)
            except:
                pass

            next_button = driver.find_element(By.CSS_SELECTOR, "button.mat-mdc-paginator-navigation-next")
            if next_button.get_attribute("aria-disabled") == "true":
                break

            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            driver.execute_script("arguments[0].click();", next_button)
            page += 1
            time.sleep(3)

        except Exception:
            print("🚫 Geen volgende pagina meer of fout bij klikken.")
            break

    driver.quit()
    return pd.DataFrame(data)
