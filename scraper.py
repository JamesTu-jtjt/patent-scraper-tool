import argparse
import os
import time
import subprocess
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By


def get_ftps_links(selected_year, download_root):
    # === Configuration ===
    url = "https://cloud.tipo.gov.tw/S220/opdata/detail/PatentIsuRegSpecXMLA"
    os.makedirs(download_root, exist_ok=True)

    # === Setup Selenium ===
    print("[INFO] Launching browser...")
    options = Options()
    options.add_argument("--headless")  # Runs browser in background
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)

    print(f"[INFO] Opening {url}")
    driver.get(url)
    time.sleep(3)
    # Find the dropdown element (usually a <select> tag)
    dropdown_element = driver.find_element(By.XPATH, '//*[@id="root"]//select')  # or use another locator
    # Create a Select object
    select = Select(dropdown_element)
    select.select_by_value(selected_year)
    print(f"[INFO] Selected year: {selected_year}")
    time.sleep(3)
    html = driver.page_source
    driver.quit()

    # === Parse HTML ===
    soup = BeautifulSoup(html, "html.parser")
    ftps_links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith("ftps://")]
    print(f"[INFO] Found {len(ftps_links)} FTPS links")

    return ftps_links


# === lftp mirror for folder-preserving downloads ===
def mirror_with_lftp(ftps_url, download_root):
    parsed = urlparse(ftps_url)
    host = parsed.hostname
    remote_path = parsed.path

    # We'll mirror into local path: downloads/selected_year
    local_mirror_path = os.path.join(download_root, remote_path.split('/')[-1])
    os.makedirs(local_mirror_path, exist_ok=True)

    print(f"[INFO] Mirroring: {remote_path}")
    cmd = [
        "lftp", "-e",
        f"set ssl:check-hostname no; open ftps://{host}; mirror --use-pget-n=4 --verbose {remote_path} .; bye"
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=local_mirror_path,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[SUCCESS] Mirrored: {remote_path}")
        return (remote_path, "Success", result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to mirror: {remote_path}")
        print(f"[ERROR] stderr:\n{e.stderr}")
        return (remote_path, "Failed", e.stderr.strip())


if __name__ == "__main__":
    # === Parse CLI arguments ===
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=str, default='114', required=True, help="Year to select on the TIPO site (e.g. 114)")
    args = parser.parse_args()
    selected_year = args.year
    download_root = selected_year
    ftps_links = get_ftps_links(selected_year, download_root)
    # === Loop through all links and mirror each ===
    download_logs = []
    for link in ftps_links:
        log = mirror_with_lftp(link, download_root)
        download_logs.append(log)
        continue

    # === Write logs ===
    log_file = os.path.join(download_root, "download_log.txt")
    with open(log_file, "w", encoding="utf-8") as f:
        for remote_path, status, message in download_logs:
            f.write(f"{remote_path}\t{status}\n{message}\n\n")

    print(f"[INFO] Download complete. Logs saved to {log_file}")
