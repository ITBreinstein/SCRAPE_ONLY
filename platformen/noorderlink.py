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

def scrape_noorderlink():
    base_url = "https://noorderlink.nl"
    base_search = (
        "https://noorderlink.nl/vacatures?"
        "language=nl&educations=5&educations=7&hours=32-40"
        "&employments=1&employments=2&employments=4"
    )

    vacatures = []
    seen_links = set()
    page = 1

    # --- 🗺️ Lees woonplaatsen.csv en maak lookup ---
    try:
        woonplaatsen = pd.read_csv("woonplaatsen.csv")
        plaats_provincie = {}
        for _, row in woonplaatsen.iterrows():
            if pd.isna(row["Plaats"]) or pd.isna(row["Provincie"]):
                continue
            eerste_plaats = str(row["Plaats"]).split("/")[0].strip().lower()
            provincie = str(row["Provincie"]).strip()
            if provincie.lower() == "fryslân":
                provincie = "Friesland"
            plaats_provincie[eerste_plaats] = provincie
    except Exception as e:
        print(f"⚠️ Kon woonplaatsen.csv niet laden ({e}), regio blijft onbewerkt.")
        plaats_provincie = {}

    # Helperfunctie: plaatsnaam → provincie
    def plaats_naar_provincie(plaats):
        if not isinstance(plaats, str) or plaats.strip() == "":
            return plaats
        plaats = plaats.strip().lower()

        if plaats in plaats_provincie:
            return plaats_provincie[plaats]

        # fuzzy match — bijv. “Groningen (stad)” → “Groningen”
        for p in plaats_provincie.keys():
            if p in plaats or plaats in p:
                return plaats_provincie[p]
        return plaats

    # --- 🔄 Pagina’s doorlopen ---
    while True:
        url = f"{base_search}&page={page}"

        r = requests.get(url)
        if r.status_code != 200:
            print(f"❌ Pagina {page} niet bereikbaar ({r.status_code}). Stoppen.")
            break

        soup = BeautifulSoup(r.text, "html.parser")

        # lees paginateller, bijv. “1/3”
        teller = soup.select_one("span.text-base.font-medium")
        if teller and "/" in teller.text:
            _, totaal = teller.text.split("/")
            totaal = int(totaal.strip())
        else:
            totaal = None

        cards = soup.select("a[href*='/vacature/']")
        if not cards:
            print("⚠️ Geen vacatures meer gevonden. Stoppen.")
            break

        nieuwe_vacatures = 0

        for card in cards:
            try:
                link = base_url + card.get("href")
                if link in seen_links:
                    continue
                seen_links.add(link)

                title_el = card.select_one("h5")
                org_el = card.select_one("span.text-base.font-medium.leading-5")

                # --- Regio ophalen ---
                regio = ""
                map_icon = card.select_one("span.i-heroicons\\:map-pin")
                if map_icon:
                    regio_el = map_icon.find_parent("span")
                    if regio_el:
                        regio = regio_el.get_text(strip=True).replace("📍", "").strip()

                # --- Plaats → Provincie ---
                provincie = plaats_naar_provincie(regio)

                titel = title_el.text.strip() if title_el else ""
                organisatie = org_el.text.strip() if org_el else ""
                volledige_titel = f"{titel} ({organisatie})".strip()

                # --- Detailpagina ophalen ---
                detail = requests.get(link)
                dsoup = BeautifulSoup(detail.text, "html.parser")
                beschrijving_el = dsoup.select_one(
                    "section.flex.flex-col.gap-6 .cms-rich-content"
                )
                beschrijving = (
                    beschrijving_el.get_text(separator="\n").strip()
                    if beschrijving_el
                    else ""
                )

                vacatures.append(
                    {
                        "Titel": volledige_titel,
                        "Regio": provincie,
                        "Link": link,
                        "Beschrijving": beschrijving,
                        "Bron": "Noorderlink",
                    }
                )

                nieuwe_vacatures += 1
                time.sleep(0.3)

            except Exception as e:
                print(f"❌ Fout bij vacature: {e}")

        # Stop als dit de laatste pagina was
        if totaal and page >= totaal:
            print("🏁 Laatste pagina bereikt volgens teller.")
            break

        if nieuwe_vacatures == 0:
            break

        page += 1
        time.sleep(1)

    # --- 📊 DataFrame ---
    df = pd.DataFrame(vacatures)
    df = df.drop_duplicates(subset=["Link"])
    return df
