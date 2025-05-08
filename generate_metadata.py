import xml.etree.ElementTree as ET
import pandas as pd
import os
import argparse

def parse_single_xml(xml_path, image_dir):
    """Parse a single XML and return a DataFrame with image metadata."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        app_no = root.findtext(".//application-reference/document-id/doc-number")
        title = root.findtext(".//invention-title/chinese-title")

        # IPC codes
        ipc_codes = []
        main_class = root.findtext(".//classification-ipc/main-classification")
        if main_class:
            ipc_codes.append(main_class)
        further_classes = root.findall(".//classification-ipc/further-classification")
        for fc in further_classes:
            ipc_codes.append(fc.text)

        # Placeholder for descriptions (could be added from external file later)
        loc_descriptions = root.findtext(".//invention-title/english-title")

        # Images from XML
        images = root.findall(".//drawings/figure/img")
        rows = []
        for i, img in enumerate(images):
            rows.append({
                "app_no": app_no,
                "img_path": image_dir,
                "rep_flag": i == 0,
                "title": title,
                "locs": ipc_codes,
                "loc_descriptions": loc_descriptions
            })

        return pd.DataFrame(rows)
    except Exception as e:
        print(f"[ERROR] Failed to parse {xml_path}: {e}")
        return pd.DataFrame()

def process_all_folders(parent_folder):
    """Process all dataset folders under the given parent."""
    for dataset_name in os.listdir(parent_folder):
        dataset_path = os.path.join(parent_folder, dataset_name)
        if not os.path.isdir(dataset_path):
            continue

        print(f"[INFO] Processing dataset: {dataset_name}")
        all_rows = []
        for xml_file in os.listdir(dataset_path):
            if not xml_file.lower().endswith(".xml"):
                continue

            xml_path = os.path.join(dataset_path, xml_file)
            image_folder_name = os.path.splitext(xml_file)[0]
            image_folder_path = os.path.join(dataset_path, image_folder_name)
            if not os.path.isdir(image_folder_path):
                print(f"[WARN] No matching image folder for {xml_file}")
                continue

            df = parse_single_xml(xml_path, image_folder_path)
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

