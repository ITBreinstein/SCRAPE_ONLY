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
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException, InvalidSessionIdException

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

def scrape_werkeninnoordoostbrabant(with_description=True):
    driver = get_chrome_driver()
    driver.set_page_load_timeout(10)

    driver.get("https://www.werkeninnoordoostbrabant.nl/vacatures?opleidingsniveau=hbo,wo")

    data = []
    page = 1

    while True:
        # ---- Sneller ophalen van vacaturekaarten ----
        try:
            vacatures = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-vacature-item"))
            )
        except TimeoutException:
            print(f"⚠️ Geen vacatures op pagina {page}. Stoppen.")
            break

        for idx in range(len(vacatures)):
            try:
                # Haal items opnieuw op (stale element fix)
                vacatures = driver.find_elements(By.CSS_SELECTOR, "app-vacature-item")
                vac = vacatures[idx]

                title = vac.find_element(By.CSS_SELECTOR, "h3.kaart__titel").text.strip()

                # ---- Sneller klikken ----
                clicked = False
                for _ in range(2):  # max 2 pogingen
                    try:
                        vac.click()
                        clicked = True
                        break
                    except:
                        driver.execute_script("arguments[0].click();", vac)

                if not clicked:
                    print(f"⚠️ Skip vacature {idx+1}: niet klikbaar")
                    continue

                # ---- Beschrijving laden (max 5 sec wachten) ----
                description = ""
                if with_description:
                    try:
                        elem = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cb-text-container.prose"))
                        )
                        description = elem.text.strip()
                    except:
                        description = ""

                link = driver.current_url

                data.append({
                    "Titel": title,
                    "Regio": "Noord-Brabant",
                    "Link": link,
                    "Beschrijving": description,
                    "Bron": "Werkeninnoordoostbrabant"
                })

                # ---- Snelle terugnavigatie ----
                try:
                    driver.back()
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-vacature-item"))
                    )
                except:
                    print("⚠️ Back mislukte → pagina opnieuw laden")
                    driver.get(driver.current_url)

            except Exception as e:
                print(f"⚠️ Fout bij vacature {idx+1} op pagina {page}: {e}")
                # NIET TOO LANG WACHTEN → gewoon skippen
                continue

        # ---- Volgende pagina ----
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "button.mat-mdc-paginator-navigation-next")

            # Check disabled
            if next_btn.get_attribute("aria-disabled") == "true":
                break

            driver.execute_script("arguments[0].click();", next_btn)
            page += 1

            # Wachten tot pagina geladen is
            WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-vacature-item"))
            )

        except Exception as e:
            print(f"⚠️ Kan volgende pagina niet vinden/klikken: {e}")
            break

    driver.quit()
    return pd.DataFrame(data)
