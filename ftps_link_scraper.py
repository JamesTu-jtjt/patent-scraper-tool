import argparse
import time
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import xml.etree.ElementTree as ET

def get_ftps_links(selected_year):
    urls = [
        "https://cloud.tipo.gov.tw/S220/opdata/detail/PatentIsuRegSpecXMLA",
        "https://cloud.tipo.gov.tw/S220/opdata/detail/PatentPubXML"
    ]
    print("[INFO] Launching browser...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    ftps_links = {}
    for url in urls:
        print(f"[INFO] Opening {url}")
        driver.get(url)
        time.sleep(3)
        dropdown_element = driver.find_element(By.XPATH, '//*[@id="root"]//select')
        select = Select(dropdown_element)
        select.select_by_value(selected_year)
        print(f"[INFO] Selected year: {selected_year}")
        time.sleep(3)
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith("ftps://")]
        for l in links:
            ref = l.split('/')[-1].split('_')[-1]
            ftps_links.setdefault(ref, []).append(l)
        print(f"[INFO] Found {len(links)} FTPS links")
    driver.quit()
    
    with open(f"ftps_links_{selected_year}.json", "w", encoding="utf-8") as f:
        json.dump(ftps_links, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Saved FTPS links to ftps_links_{selected_year}.json")

    return ftps_links

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=str, default='114', required=True, help="Year to select on the TIPO site (e.g. 114)")
    args = parser.parse_args()
    selected_year = args.year
    ftps_links = get_ftps_links(selected_year)
    print(f"[INFO] FTPS link scraping complete.")
