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

def scrape_werkeninzuidoostbrabant(with_description=True):

    driver = get_chrome_driver()
    driver.set_page_load_timeout(30)
    driver.get("https://www.werkeninzuidoostbrabant.nl/vacatures?opleidingsniveau=hbo,wo")
    time.sleep(5)

    data = []
    page = 1

    while True:
        try:
            # Wacht tot vacatures zichtbaar zijn
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-vacature-item"))
            )
            vacatures = driver.find_elements(By.CSS_SELECTOR, "app-vacature-item")
            #print(f"📄 Pagina {page}: {len(vacatures)} vacatures gevonden.\n")
        except TimeoutException:
            #print(f"⚠️ Geen vacatures gevonden op pagina {page}.")
            break

        for idx in range(len(vacatures)):
            try:
                # Haal lijst opnieuw op om stale element te vermijden
                vacatures = driver.find_elements(By.CSS_SELECTOR, "app-vacature-item")
                vac = vacatures[idx]

                # Titel
                titel = vac.find_element(By.CSS_SELECTOR, "h3.kaart__titel").text.strip()

                # Klik op vacature
                driver.execute_script("arguments[0].scrollIntoView(true);", vac)
                try:
                    vac.click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", vac)
                time.sleep(2)

                # Beschrijving
                beschrijving = ""
                if with_description:
                    try:
                        content_el = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cb-text-container.prose"))
                        )
                        beschrijving = content_el.get_attribute("innerText").strip()
                    except:
                        beschrijving = ""

                # Link = huidige URL
                link = driver.current_url

                data.append({
                    "Titel": titel,
                    "Regio": "Noord-Brabant",
                    "Link": link,
                    "Beschrijving": beschrijving,
                    "Bron": "Werkeninzuidoostbrabant"
                })
                #print(f"[Pagina {page} - Vacature {idx+1}/{len(vacatures)}] ✅ {titel}")

                # Terug naar overzicht
                driver.back()
                time.sleep(3)

            except StaleElementReferenceException:
                print(f"⚠️ Stale element bij vacature {idx+1} op pagina {page}, opnieuw proberen...")
                time.sleep(2)
                continue
            except Exception as e:
                print(f"⚠️ Fout bij vacature {idx+1} op pagina {page}: {e}")
                driver.back()
                time.sleep(2)
                continue

        # Volgende pagina
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "button.mat-mdc-paginator-navigation-next")
            # Controleer aria-disabled attribuut in plaats van alleen class
            if next_btn.get_attribute("aria-disabled") == "true":
                #print(f"✅ Laatste pagina {page} bereikt.")
                break
            # Scroll en klik
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            driver.execute_script("arguments[0].click();", next_btn)
            page += 1
            time.sleep(5)  # wacht tot de nieuwe pagina geladen is
        except Exception as e:
            #print(f"⚠️ Kan volgende pagina niet vinden of klikken: {e}")
            break

    driver.quit()
    df = pd.DataFrame(data)
    #print(f"\n📄 Totaal {len(df)} vacatures succesvol opgehaald.")
    return df
