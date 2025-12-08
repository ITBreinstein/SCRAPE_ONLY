# scraper_core.py
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
import threading

from platformen.striive import scrape_striive
from platformen.flextender import scrape_flextender
from platformen.yacht import scrape_yacht
from platformen.igom import scrape_igom
from platformen.werkenvoornederland import scrape_werkenvoornederland
from platformen.werkeninnoordoostbrabant import scrape_werkeninnoordoostbrabant
from platformen.werkeninzuidoostbrabant import scrape_werkeninzuidoostbrabant
from platformen.gemeentebanen import scrape_gemeentebanen
from platformen.greenjobs import scrape_greenjobs
from platformen.werkeninnoordhollandnoord import scrape_werkeninnoordhollandnoord
from platformen.werkeninfriesland import scrape_werkeninfriesland
from platformen.werkenvoorgroningen import scrape_werkenvoorgroningen
from platformen.vooruitindrenthe import scrape_vooruitindrenthe
from platformen.werkenaanhetnoorden import scrape_werkenaanhetnoorden
from platformen.noordnederlandwerkt import scrape_noordnederlandwerkt
from platformen.noorderlink import scrape_noorderlink
from platformen.vacaturebanknoordnederland import scrape_vacaturebanknoordnederland
from platformen.vacaturesnoordholland import scrape_vacaturesnoordholland
from platformen.werkenbijnod import scrape_werkenbijnod

def run_with_timeout(func, timeout_seconds):
    result = {}

    def wrapper():
        try:
            result["data"] = func()
        except Exception as e:
            result["error"] = e

    thread = threading.Thread(target=wrapper)
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        return "timeout"
    if "error" in result:
        return result["error"]

    return result.get("data")

def scrape_all_jobs():
    start_time = time.time()
    dfs = []

    SCRAPERS = [
        ("Striive", scrape_striive),
        ("Flextender", scrape_flextender),
        ("Yacht", scrape_yacht),
        ("IGOM", scrape_igom),
        ("Werkenvoornederland", scrape_werkenvoornederland),
        ("Werkeninnoordoostbrabant", scrape_werkeninnoordoostbrabant),
        ("Werkeninzuidoostbrabant", scrape_werkeninzuidoostbrabant),
        ("Gemeentebanen", scrape_gemeentebanen),
        ("Greenjobs", scrape_greenjobs),
        ("Werkeninnoordhollandnoord", scrape_werkeninnoordhollandnoord),
        ("Werkeninfriesland", scrape_werkeninfriesland),
        ("Werkenvoorgroningen", scrape_werkenvoorgroningen),
        ("Vooruitindrenthe", scrape_vooruitindrenthe),
        ("Werkenaanhetnoorden", scrape_werkenaanhetnoorden),
        ("Noordnederlandwerkt", scrape_noordnederlandwerkt),
        ("Noorderlink", scrape_noorderlink),
        ("Vacaturebanknoordnederland", scrape_vacaturebanknoordnederland),
        ("Vacaturesnoordholland", scrape_vacaturesnoordholland),
        ("Werkenbijnod", scrape_werkenbijnod),
    ]

    TIMEOUT_SECONDS = 2600  # 10 minuten per site

    for name, func in SCRAPERS:
        print(f"➡️ Start scrape: {name}")

        out = run_with_timeout(func, TIMEOUT_SECONDS)

        # --- FIX: no ambiguity ----
        if isinstance(out, str) and out == "timeout":
            print(f"⏭️ {name} overgeslagen (timeout van {TIMEOUT_SECONDS} sec)")
            continue

        if isinstance(out, Exception):
            print(f"❌ Fout tijdens scraping {name}: {out}")
            continue

        if isinstance(out, pd.DataFrame):
            dfs.append(out)
            print(f"✅ {name} done, {len(out)} rows")
            continue

        print(f"⚠️ {name}: onverwacht resultaat type: {type(out)} -> {out}")

    # Combine to final DF
    df_combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    duration = time.time() - start_time
    print(f"⏱️ Scraping afgerond in {duration/60:.1f} minuten")

    return df_combined
