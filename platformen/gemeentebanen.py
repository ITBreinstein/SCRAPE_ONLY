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

def scrape_gemeentebanen(with_description=True, woonplaatsen_csv="woonplaatsen.csv", max_pages=12):
    driver = get_chrome_driver()
    driver.set_page_load_timeout(30)
    base_url = (
        "https://www.gemeentebanen.nl/vacatures?"
        "distance=10&fromStaffingAgency=INCLUDE&education=hbo%2Cwo&"
        "discipline=administratief-secretarieel%2Cautomatisering-ict%2Cbestuurlijk%2C"
        "binnendienst-algemene-dienst%2Cburger-publiekszaken%2Cfinancieel-economisch%2C"
        "dienstverlening-facilitair%2Cjuridisch%2Cpersoneel-organisatie"
    )

    driver.get(base_url)

    # Cookie-banner sluiten
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "jr-cookie-modal"))
        )
        driver.execute_script("document.getElementById('jr-cookie-modal').style.display='none';")
        #print("✅ Cookie-banner verborgen.")
    except TimeoutException:
        print("ℹ️ Geen cookie-banner gevonden.")

    all_data = []
    visited_pages = set()
    page = 1

    while True:
        #print(f"📄 Scrapen van pagina {page}...")

        # Stop bij max_pages
        if page > max_pages:
            #print(f"✅ Maximaal aantal pagina’s ({max_pages}) bereikt, stoppen.")
            break

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li .vacancy-card"))
            )
        except TimeoutException:
            print(f"❌ Vacatures niet gevonden op pagina {page}.")
            break

        current_url = driver.current_url
        if current_url in visited_pages:
            print("⚠️ Pagina al bezocht, stoppen.")
            break
        visited_pages.add(current_url)

        vacatures = driver.find_elements(By.CSS_SELECTOR, "li .vacancy-card")

        for v in vacatures:
            titel = regio = link = beschrijving = None
            try:
                titel = v.find_element(By.CSS_SELECTOR, ".text-primary-500").text.strip()
            except:
                pass
            try:
                regio = v.find_element(By.CSS_SELECTOR, ".vacancy-tag.location span:last-child").text.strip()
            except:
                pass
            try:
                link = v.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            except:
                pass

            if with_description and link:
                try:
                    driver.execute_script(f"window.open('{link}', '_blank');")
                    driver.switch_to.window(driver.window_handles[-1])
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.responsive-wrapper.font-content"))
                    )
                    beschrijving_el = driver.find_element(
                        By.CSS_SELECTOR,
                        "div.prose.prose-lg.raw-html.ck-content.jb-list.list-primary.triangle-bullet.text-gray-800.prose-blue"
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
                "Bron": "gemeentebanen"
            })

        # Zoek naar volgende pagina-knop
        try:
            next_btn = driver.find_element(By.XPATH, "//a[span[@class='sr-only' and text()='Volgende']]")
            disabled_attr = next_btn.get_attribute("disabled")
            if disabled_attr == "" or disabled_attr is not None:
                #print("✅ Laatste pagina bereikt, stoppen.")
                break

            next_href = next_btn.get_attribute("href")
            if not next_href:
                print("✅ Geen volgende link, stoppen.")
                break

            if next_href.startswith("?"):
                next_href = "https://www.gemeentebanen.nl/vacatures" + next_href

            driver.get(next_href)
            page += 1
            time.sleep(2)

        except NoSuchElementException:
            #print("✅ Geen volgende knop meer, stoppen.")
            break

    driver.quit()

    df = pd.DataFrame(all_data)

    # Dubbele vacatures verwijderen (titel + link)
    df = df.drop_duplicates(subset=["Titel", "Link"]).reset_index(drop=True)
    df = df.drop_duplicates(subset=["Beschrijving"])

    # Regio naar Provincie
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
        print(f"⚠️ Provincie mapping mislukt: {e}")
        df["Regio"] = df["Regio"].fillna("Onbekend")

    df.drop_duplicates()
    return df
