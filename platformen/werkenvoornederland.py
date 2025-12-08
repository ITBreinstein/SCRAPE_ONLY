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

def scrape_werkenvoornederland(with_description=True, max_scrolls=30):
    import requests
    from bs4 import BeautifulSoup
    from selenium.common.exceptions import NoSuchElementException
    import pandas as pd
    import time

    # ------------------------------------------------------
    # Snelle HTML scraper voor detailpagina (email + tekst)
    # ------------------------------------------------------
    def fetch_detail_data(link, title):
        try:
            resp = requests.get(link, timeout=(5, 15))
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Email
            email = ""
            email_el = soup.select_one("a[href^='mailto:']")
            if email_el:
                email = email_el.text.strip()

            # Beschrijving
            beschrijving = ""
            if with_description:
                sections = soup.select("div.s-article-content")
                beschrijving = "\n\n".join([s.get_text(strip=True) for s in sections])

            return email, beschrijving

        except Exception as e:
            print(f"⚠️ Detailpagina mislukt ({title}): {e}")
            return "", ""

    # ------------------------------------------------------
    # Start driver en laad lijstpagina
    # ------------------------------------------------------
    driver = get_chrome_driver()
    driver.set_page_load_timeout(20)

    driver.get(
        "https://www.werkenvoornederland.nl/vacatures?"
        "type=vacature&werkdenkniveau=CWD.04%2CCWD.08&"
        "vakgebied=CVG.02%2CCVG.32%2CCVG.08"
    )
    time.sleep(2)

    # ------------------------------------------------------
    # Scroll tot alles geladen is
    # ------------------------------------------------------
    last_count = 0
    for _ in range(max_scrolls):
        vacatures = driver.find_elements(By.CSS_SELECTOR, "div.vacancy-list__item section.vacancy")

        if len(vacatures) == last_count:
            break  # niets nieuws → stoppen

        last_count = len(vacatures)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

    vacatures = driver.find_elements(By.CSS_SELECTOR, "div.vacancy-list__item section.vacancy")
    print(f"➡️ gevonden vacatures: {len(vacatures)}")

    # ------------------------------------------------------
    # Parse alle kaarten
    # ------------------------------------------------------
    data = []
    seen_links = set()

    for idx, vac in enumerate(vacatures):
        try:
            # Titel + Link
            title_el = vac.find_element(By.CSS_SELECTOR, "h2.vacancy__title a")
            title = title_el.text.strip()
            link = title_el.get_attribute("href")
            if not link.startswith("http"):
                link = "https://www.werkenvoornederland.nl" + link

            if link in seen_links:
                continue
            seen_links.add(link)

            # Plaats
            try:
                plaats = vac.find_element(By.CSS_SELECTOR,
                    "li.job-short-info__item-icon span.job-short-info__value-icon"
                ).text.strip()
            except NoSuchElementException:
                plaats = ""

            # Opdrachtgever
            try:
                opdrachtgever = vac.find_element(By.CSS_SELECTOR, "p.vacancy__employer").text.strip()
            except:
                opdrachtgever = ""

            # ---- SNEL detail ophalen via requests ----
            email, beschrijving = fetch_detail_data(link, title)

            data.append({
                "Titel": title,
                "Plaats": plaats,
                "Regio": plaats,  # later gemapt
                "Opdrachtgever": opdrachtgever,
                "Email": email,
                "Link": link,
                "Beschrijving": beschrijving,
                "Bron": "Werken voor Nederland"
            })

        except Exception as e:
            print(f"⚠️ Fout bij vacature {idx+1}: {e}")
            continue

    driver.quit()

    df = pd.DataFrame(data)

    # ------------------------------------------------------
    # Mapping Plaats → Provincie
    # ------------------------------------------------------
    woonplaatsen_df = pd.read_csv("woonplaatsen.csv")
    plaats_to_provincie = dict(zip(
        woonplaatsen_df['Plaats'].str.lower().str.strip(),
        woonplaatsen_df['Provincie'].str.strip()
    ))

    df["Regio"] = df["Plaats"].str.lower().map(plaats_to_provincie).fillna(df["Plaats"])
    return df
