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

def scrape_vacaturebanknoordnederland():
    # Laad woonplaatsen -> provincies mapping
    woonplaatsen_df = pd.read_csv("woonplaatsen.csv")  # kolommen: Plaats, Provincie
    plaats_to_prov = dict(zip(woonplaatsen_df["Plaats"], woonplaatsen_df["Provincie"]))

    base_url = "https://vacaturebank-noordnederland.nl"
    base_search = (
        "https://vacaturebank-noordnederland.nl/vacatures?"
        "filters[keyword]=&filters[city_id]=&filters[radius]=&"
        "filters[industries][0]=6&filters[tenant]=&filters[date]="
    )

    vacatures = []
    seen_links = set()
    page = 1

    while True:
        url = f"{base_search}&page={page}"

        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            print(f"❌ Pagina {page} niet bereikbaar ({r.status_code}). Stoppen.")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a[href^='/vacature/'].group.relative.mb-4")
        if not cards:
            break

        nieuwe_vacatures = 0

        for card in cards:
            try:
                link = base_url + card.get("href")
                if link in seen_links:
                    continue
                seen_links.add(link)

                # Titel
                title_el = card.select_one("h4")
                title = title_el.get_text(strip=True) if title_el else ""

                # Regio (provincie via woonplaatsen)
                regio = ""
                regio_el = card.select_one("li.flex.items-center.gap-2 span.truncate")
                if regio_el:
                    tekst = regio_el.get_text(strip=True).lower()
                    for plaats, prov in plaats_to_prov.items():
                        if plaats.lower() in tekst:
                            regio = prov
                            break
                    if not regio:
                        regio = tekst  # fallback: originele tekst

                # Korte teaser
                teaser_el = card.select_one("p.mt-5")
                teaser = teaser_el.get_text(strip=True) if teaser_el else ""

                # Detailpagina
                detail = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
                dsoup = BeautifulSoup(detail.text, "html.parser")
                beschrijving_el = dsoup.select("div.cms-text")
                beschrijving = "\n\n".join(
                    el.get_text(separator="\n").strip() for el in beschrijving_el
                )
                beschrijving = beschrijving if beschrijving else teaser

                vacatures.append({
                    "Titel": title,
                    "Regio": regio,
                    "Link": link,
                    "Beschrijving": beschrijving,
                    "Bron": "Vacaturebank Noord Nederland"
                })

                nieuwe_vacatures += 1
                time.sleep(0.4)

            except Exception as e:
                print(f"❌ Fout bij vacature: {e}")

        if nieuwe_vacatures == 0:
            break

        page += 1
        time.sleep(1)

    # Dataframe
    df = pd.DataFrame(vacatures)
    df = df.drop_duplicates(subset=["Link"])

    return df

