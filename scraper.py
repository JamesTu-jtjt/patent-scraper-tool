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
import xml.etree.ElementTree as ET


def get_ftps_links(selected_year):
    # === Configuration ===
    urls = ["https://cloud.tipo.gov.tw/S220/opdata/detail/PatentIsuRegSpecXMLA",
            "https://cloud.tipo.gov.tw/S220/opdata/detail/PatentPubXML"]

    # === Setup Selenium ===
    print("[INFO] Launching browser...")
    options = Options()
    options.add_argument("--headless")  # Runs browser in background
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    ftps_links = {}
    for url in urls:
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

        # === Parse HTML ===
        soup = BeautifulSoup(html, "html.parser")
        links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith("ftps://")]
        for l in links: 
            ref = l.split('/')[-1].split('_')[-1]
            if ref in ftps_links:
                ftps_links[ref].append(l)
            else: 
                ftps_links[ref] = [l]
        print(f"[INFO] Found {len(links)} FTPS links")
    driver.quit()
    return ftps_links

def download_index_xml(ftps_url, temp_dir):
    parsed = urlparse(ftps_url[0])
    host = parsed.hostname
    remote_path = parsed.path
    remote_index_path = os.path.join(remote_path, "index.xml")
    os.makedirs(temp_dir, exist_ok=True)
    cmd = [
        "lftp", "-e",
        f"set ssl:check-hostname no; open ftps://{host}; get {remote_index_path}; bye"
    ]
    try:
        result = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True, check=True)
        print(f"[SUCCESS] Downloaded index.xml from {remote_path}")
        return os.path.join(temp_dir, "index.xml")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to download index.xml from {remote_path}")
        print(e.stderr)
        return None

def get_design_doc_numbers(index_path):
    try:
        tree = ET.parse(index_path)
        root = tree.getroot()
        design_docs = []
        for grant in root.findall(".//tw-patent-grant"):
            volno = grant.findtext(".//volno")
            isuno = grant.findtext(".//isuno")
            publ = grant.find(".//publication-reference")
            appl = grant.find(".//application-reference")
            if appl is not None and appl.attrib.get("appl-type") == "design":
                doc_number = appl.findtext("document-id/doc-number")
                pub_ref = publ.findtext("document-id/doc-number")
                if doc_number and pub_ref:
                    if len(isuno) == 1: 
                        isuno = '0' + isuno
                    xml_name = volno + isuno + pub_ref
                    design_docs.append([doc_number, xml_name])
        print(f"[INFO] Found {len(design_docs)} design applications.")
        return design_docs
    except Exception as e:
        print(f"[ERROR] Parsing failed for {index_path}: {e}")
        return []

def download_design_docs(ftps_url, doc_numbers, download_root):
    # Get PatentIsuRegSpec
    spec_parsed = urlparse(ftps_url[0])
    spec_host = spec_parsed.hostname
    spec_remote_path = spec_parsed.path
    parsed = urlparse(ftps_url[1])
    host = parsed.hostname
    remote_path = parsed.path
    os.makedirs(download_root, exist_ok=True)
    for doc_no in doc_numbers[:3]:
        print(f"[INFO] Downloading files for doc-number: {doc_no[0]}")
        cur_path = os.path.join(download_root, doc_no[1])
        cur_path = os.path.join(cur_path, "PatentIsuRegSpecXMLA")
        os.makedirs(cur_path, exist_ok=True)
        # Download XML
        xml_cmd = [
            "lftp", "-e",
            f"set ssl:check-hostname no; open ftps://{spec_host}; get {spec_remote_path}/{doc_no[0]}.xml; bye"
        ]
        try:
            subprocess.run(xml_cmd, cwd=cur_path, capture_output=True, text=True, check=True)
            print(f"[SUCCESS] Downloaded {doc_no[0]}.xml")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to download {doc_no[0]}.xml: {e.stderr.strip()}")

        print(f"[INFO] Downloading files for doc-number: {doc_no[1]}")
        # Download folder
        folder_cmd = [
            "lftp", "-e",
            f"set ssl:check-hostname no; open ftps://{host}; mirror --use-pget-n=4 {remote_path}/{doc_no[1]} {doc_no[1]}; bye"
        ]
        try:
            subprocess.run(folder_cmd, cwd=download_root, capture_output=True, text=True, check=True)
            print(f"[SUCCESS] Mirrored folder: {doc_no[1]}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to mirror folder {doc_no[1]}: {e.stderr.strip()}")


if __name__ == "__main__":
    # === Parse CLI arguments ===
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=str, default='114', required=True, help="Year to select on the TIPO site (e.g. 114)")
    args = parser.parse_args()
    selected_year = args.year
    ftps_links = get_ftps_links(selected_year)
    for ref in ftps_links:
        if len(ftps_links[ref]) < 2: 
            continue
        download_root = args.year # os.path.basename(urlparse(link).path.rstrip("/"))
        download_root = os.path.join(download_root, ftps_links[ref][0].split('/')[-1].split('_')[-1])
        index_path = download_index_xml(ftps_links[ref], download_root)
        if not index_path:
            continue
        doc_numbers = get_design_doc_numbers(index_path)
        if doc_numbers:
            download_design_docs(ftps_links[ref], doc_numbers, download_root)

    print(f"[INFO] Download complete.")
