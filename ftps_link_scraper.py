import argparse
import time
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import xml.etree.ElementTree as ET

# Define the main function that scrapes FTPS links for a selected year
def get_ftps_links(selected_year):
    # URLs to visit and extract links from
    urls = [
        "https://cloud.tipo.gov.tw/S220/opdata/detail/PatentIsuRegSpecXMLA",
        "https://cloud.tipo.gov.tw/S220/opdata/detail/PatentPubXML"
    ]

    print("[INFO] Launching browser...")

    # Configure Selenium Chrome options for headless browsing (no GUI)
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    # Launch the Chrome browser with the specified options
    driver = webdriver.Chrome(options=options)

    # Dictionary to hold all the FTPS links categorized by file reference
    ftps_links = {}

    # Iterate over each URL to scrape FTPS links
    for url in urls:
        print(f"[INFO] Opening {url}")
        driver.get(url)
        # Wait for the page to load
        time.sleep(3)

        # Locate the year dropdown and select the desired year
        dropdown_element = driver.find_element(By.XPATH, '//*[@id="root"]//select')
        select = Select(dropdown_element)
        select.select_by_value(selected_year)
        print(f"[INFO] Selected year: {selected_year}")
        # Wait for the page to update based on selection
        time.sleep(3)

        # Get the page HTML and parse it with BeautifulSoup
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # Find all 'a' tags with FTPS links
        links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith("ftps://")]

        # Extract the reference from the link and group links accordingly
        for l in links:
            # Get the volume no. and issue no.
            ref = l.split('/')[-1].split('_')[-1]
            ftps_links.setdefault(ref, []).append(l)

        print(f"[INFO] Found {len(links)} FTPS links")

    # Close the browser after processing all URLs
    driver.quit()

    # Save the FTPS links dictionary to a JSON file
    with open(f"ftps_links_{selected_year}.json", "w", encoding="utf-8") as f:
        json.dump(ftps_links, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Saved FTPS links to ftps_links_{selected_year}.json")

    return ftps_links

# Entry point of the script
if __name__ == "__main__":
    # Set up argument parser to accept year from command line
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=str, default='114', required=True, help="Year to select on the TIPO site (e.g. 114)")
    args = parser.parse_args()

    # Call the scraping function with the provided year
    selected_year = args.year
    ftps_links = get_ftps_links(selected_year)

    print(f"[INFO] FTPS link scraping complete.")
