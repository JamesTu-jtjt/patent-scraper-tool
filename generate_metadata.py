import xml.etree.ElementTree as ET
import pandas as pd
import os
import argparse

def parse_single_patent(folder_path):
    """Parse a single patent's data and return a DataFrame with image metadata."""
    try:
        spec_path = os.path.join(folder_path, "PatentIsuRegSpecXMLA")
        spec_xml_file = os.listdir(spec_path)[0]
        spec_tree = ET.parse(os.path.join(spec_path, spec_xml_file))
        spec_root = spec_tree.getroot()
        xml_file = ""
        for file in os.listdir(folder_path):
            if file.lower().endswith(".xml"):
                xml_file = file
        tree = ET.parse(os.path.join(folder_path, xml_file))
        root = tree.getroot()
        specifications = root.find("./specification")
        # application number
        app_no = spec_root.findtext(".//application-reference/document-id/doc-number")
        # img_path & rep_flag
        img_paths = []
        rep_flags = []
        rep = False
        images = root.findall(".//drawings/figure/img")
        for i, img in enumerate(images):
            img_path = os.path.join(folder_path, img.attrib.get("file"))
            rep_flag = "FALSE"
            if root.findall(".//drawings/figure")[i].attrib.get("representative") == "y":
                print("Found REPRESENTATIVE")
                rep_flag = "TRUE"
                rep = True
            img_paths.append(img_path)
            rep_flags.append(rep_flag)
        if not rep:
            rep_flags[0] = "TRUE"
        # title
        title = spec_root.findtext(".//invention-title/chinese-title")
        # locs
        locarno = spec_root.findtext(".//classification-locarno/main-classification")
        # loc_descriptions
        loc_descriptions = spec_root.findtext(".//invention-title/english-title")

        rows = []

        for i, img in enumerate(images):
            rows.append({
                "app_no": app_no,
                "img_path": img_paths[i],
                "rep_flag": rep_flags[i],
                "title": title,
                "locs": locarno,
                "loc_descriptions": loc_descriptions
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"[ERROR] Failed to parse {folder_path}: {e}")
        return pd.DataFrame()

def process_all_folders(parent_folder):
    """Process all dataset folders under the given parent."""
    for dataset_name in os.listdir(parent_folder):
        dataset_path = os.path.join(parent_folder, dataset_name)
        if not os.path.isdir(dataset_path):
            continue
        print(f"[INFO] Processing dataset: {dataset_name}")
        all_rows = []
        for folder in os.listdir(dataset_path):
            folder_path = os.path.join(dataset_path, folder)
            if os.path.isfile(folder_path):
                continue
            df = parse_single_patent(folder_path)
            if not df.empty:
                all_rows.append(df)
        if all_rows:
            final_df = pd.concat(all_rows, ignore_index=True)
            csv_path = os.path.join(parent_folder, dataset_name + "_metadata.csv")
            final_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"[INFO] Wrote {len(final_df)} rows to {csv_path}")
        else:
            print(f"[INFO] No valid XML/Image pairs in {dataset_name}")

if __name__ == "__main__":
    # === Parse CLI arguments ===
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=str, default='example', help="Folder to generate metadata")
    args = parser.parse_args()
    root_folder = args.root
    process_all_folders(root_folder)
    print("Metadata Generated.")

