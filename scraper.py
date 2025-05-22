import argparse
import os
import subprocess
import json
import shutil
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from ftps_link_scraper import get_ftps_links  # Import custom scraper

# === Load FTPS link JSON file or generate one if not found ===
def load_ftps_links(year):
    path = f"ftps_links_{year}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print(f"FTPS links file not found: Generating FTPS links file")
        return get_ftps_links(year)  # Generate and save then load again

# === Load log of successfully downloaded document IDs ===
def load_success_log(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

# === Save updated success log to JSON ===
def save_success_log(path, success_set):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(success_set), f, ensure_ascii=False, indent=2)

# === Download 'index.xml' file from FTPS to temp_dir ===
def download_index_xml(ftps_url, temp_dir):
    parsed = urlparse(ftps_url[0])
    host = parsed.hostname
    remote_path = parsed.path
    remote_index_path = os.path.join(remote_path, "index.xml")
    os.makedirs(temp_dir, exist_ok=True)

    # Skip download if already exists
    if os.path.exists(os.path.join(temp_dir, "index.xml")):
        return os.path.join(temp_dir, "index.xml")

    # Use lftp to download the file
    cmd = [
        "lftp", "-e",
        f"set ssl:check-hostname no; open ftps://{host}; get {remote_index_path}; bye"
    ]
    try:
        subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True, check=True)
        print(f"[SUCCESS] Downloaded index.xml from {remote_path}")
        return os.path.join(temp_dir, "index.xml")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to download index.xml from {remote_path}")
        print(e.stderr)
        return None

# === Parse index.xml to extract design patent document numbers and filenames ===
def get_design_doc_numbers(index_path):
    try:
        tree = ET.parse(index_path)
        root = tree.getroot()
        design_docs = []

        # Loop through each <tw-patent-grant> to extract info
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
                        isuno = '0' + isuno  # Pad isuno if issue number less than 10
                    xml_name = volno + isuno + pub_ref
                    design_docs.append([doc_number, xml_name])

        print(f"[INFO] Found {len(design_docs)} design applications.")
        return design_docs
    except Exception as e:
        print(f"[ERROR] Parsing failed for {index_path}: {e}")
        return []

# === Download XML and associated folder data for each design patent ===
def download_design_docs(ftps_url, doc_numbers, download_root):
    # Parse URLs for XML file and folder structure
    spec_parsed = urlparse(ftps_url[0])
    spec_host = spec_parsed.hostname
    spec_remote_path = spec_parsed.path

    parsed = urlparse(ftps_url[1])
    host = parsed.hostname
    remote_path = parsed.path

    os.makedirs(download_root, exist_ok=True)
    summary_log = []

    # Load previously successful downloads
    success_log_path = os.path.join(download_root, "success_log.json")
    success_set = load_success_log(success_log_path)

    # Process each document
    for doc_id, xml_name in doc_numbers:
        cur_path = os.path.join(download_root, xml_name)
        os.makedirs(cur_path, exist_ok=True)

        # Skip if already downloaded
        if doc_id in success_set:
            print(f"[SKIP] Already completed: {xml_name}")
            continue

        # Clean up folder if files already exist
        elif len(os.listdir(cur_path)) > 0:
            for filename in os.listdir(cur_path):
                file_path = os.path.join(cur_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))

        print(f"[INFO] Downloading files for doc-number: {xml_name}")

        # === Download XML file ===
        cur_path = os.path.join(cur_path, "PatentIsuRegSpecXMLA")
        os.makedirs(cur_path, exist_ok=True)
        xml_status = "Success"
        xml_cmd = [
            "lftp", "-e",
            f"set ssl:check-hostname no; open ftps://{spec_host}; get {spec_remote_path}/{doc_id}.xml; bye"
        ]
        try:
            subprocess.run(xml_cmd, cwd=cur_path, capture_output=True, text=True, check=True)
            print(f"[SUCCESS] Downloaded {doc_id}.xml")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to download {doc_id}.xml: {e.stderr.strip()}")
            xml_status = "Failed"

        # === Mirror the image/data folder ===
        folder_status = "Success"
        folder_cmd = [
            "lftp", "-e",
            f"set ssl:check-hostname no; open ftps://{host}; mirror --use-pget-n=4 {remote_path}/{xml_name} {xml_name}; bye"
        ]
        try:
            subprocess.run(folder_cmd, cwd=download_root, capture_output=True, text=True, check=True)
            print(f"[SUCCESS] Mirrored folder: {xml_name}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to mirror folder {xml_name}: {e.stderr.strip()}")
            folder_status = "Failed"

        # === Log success if both downloads succeeded ===
        if xml_status != "Failed" and folder_status != "Failed":
            success_set.add(doc_id)
            save_success_log(success_log_path, success_set)

        # Add to summary log
        summary_log.append((doc_id, xml_name, xml_status, folder_status))

    # === Write summary log to CSV ===
    log_path = os.path.join(download_root, "summary_log.csv")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("doc_number,xml_file,xml_status,folder_status\n")
        for entry in summary_log:
            f.write(",".join(entry) + "\n")
    print(f"[INFO] Summary log written to {log_path}")

# === Main execution block ===
if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=str, required=True, help="Year to get patent data.")
    args = parser.parse_args()

    # Load or generate FTPS links
    selected_year = args.year
    ftps_links = load_ftps_links(selected_year)

    # Process each group of links
    for ref in ftps_links:
        # Skip if not enough links for processing
        if len(ftps_links[ref]) < 2:
            continue

        # Define paths
        download_root = os.path.join(args.year, ref)
        temp_dir = os.path.join(download_root, "_temp")

        # Step 1: Download and parse index.xml
        index_path = download_index_xml(ftps_links[ref], temp_dir)
        if not index_path:
            continue

        # Step 2: Extract design patent document numbers
        doc_numbers = get_design_doc_numbers(index_path)

        # Step 3: Download XML and folder content
        if doc_numbers:
            download_design_docs(ftps_links[ref], doc_numbers, download_root)

    print(f"[INFO] Download complete.")
