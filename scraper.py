import argparse
import os
import subprocess
import json
import shutil
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from ftps_link_scraper import get_ftps_links

def load_ftps_links(year):
    path = f"ftps_links_{year}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print(f"FTPS links file not found: Generating FTPS links file")
        get_ftps_links(year)
        return get_ftps_links(year)
    
def load_success_log(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_success_log(path, success_set):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(success_set), f, ensure_ascii=False, indent=2)

def download_index_xml(ftps_url, temp_dir):
    parsed = urlparse(ftps_url[0])
    host = parsed.hostname
    remote_path = parsed.path
    remote_index_path = os.path.join(remote_path, "index.xml")
    os.makedirs(temp_dir, exist_ok=True)
    if os.path.exists(os.path.join(temp_dir, "index.xml")):
        return os.path.join(temp_dir, "index.xml")
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
    spec_parsed = urlparse(ftps_url[0])
    spec_host = spec_parsed.hostname
    spec_remote_path = spec_parsed.path
    parsed = urlparse(ftps_url[1])
    host = parsed.hostname
    remote_path = parsed.path

    os.makedirs(download_root, exist_ok=True)
    summary_log = []
    success_log_path = os.path.join(download_root, "success_log.json")
    success_set = load_success_log(success_log_path)

    for doc_id, xml_name in doc_numbers:
        print(f"[INFO] Downloading files for doc-number: {doc_id}")
        cur_path = os.path.join(download_root, xml_name, "PatentIsuRegSpecXMLA")
        os.makedirs(cur_path, exist_ok=True)
        if doc_id in success_set:
            print(f"[SKIP] Already completed: {doc_id}")
            continue
        else:
            for filename in os.listdir(cur_path):
                file_path = os.path.join(cur_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))
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
            if xml_status != "Failed" and folder_status != "Failed":
                success_set.add(doc_id)
                save_success_log(success_log_path, success_set)
        summary_log.append((doc_id, xml_name, xml_status, folder_status))

    log_path = os.path.join(download_root, "summary_log.csv")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("doc_number,xml_file,xml_status,folder_status\n")
        for entry in summary_log:
            f.write(",".join(entry) + "\n")
    print(f"[INFO] Summary log written to {log_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=str, required=True, help="Year to get patent data. ")
    args = parser.parse_args()
    selected_year = args.year
    ftps_links = load_ftps_links(selected_year)
    for ref in ftps_links:
        if len(ftps_links[ref]) < 2:
            continue
        download_root = os.path.join(args.year, ref)
        temp_dir = os.path.join(download_root, "_temp")
        index_path = download_index_xml(ftps_links[ref], temp_dir)
        if not index_path:
            continue
        doc_numbers = get_design_doc_numbers(index_path)
        if doc_numbers:
            download_design_docs(ftps_links[ref], doc_numbers, download_root)
    print(f"[INFO] Download complete.")
