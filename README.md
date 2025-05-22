# Patent Scraper & Metadata Generator

This project automates the retrieval of **design patent data** from the Taiwan Intellectual Property Office (TIPO) via FTPS, and generates structured metadata from the downloaded XML and image datasets.

---

## Overview

* **`ftps_link_scraper.py`**: Extracts FTPS links from the TIPO public data portal based on a selected year using Selenium + BeautifulSoup.
* **`scraper.py`**: Uses the FTPS links to download `index.xml`, individual patent XML files, and associated folders using `lftp`. Downloads are tracked and retried intelligently.
* **`generate_metadata.py`**: Parses the downloaded XML content to extract image paths, classification information, and metadata. Outputs structured `.csv` files.
* **`run_all.sh`**: Bash script to run the full pipeline (scraping, downloading, and metadata generation) with a single command.

---

## Requirements

* **Python 3.7+**

* **Google Chrome** browser

* **ChromeDriver** (place in project root or set in system PATH)

* **[lftp](https://lftp.yar.ru/)** (for FTPS downloads)
  *\*Please restart your terminal after installation.*

* Required Python packages:

  * `selenium`
  * `beautifulsoup4`
  * `pandas`

Install with:

```bash
pip install -r requirements.txt
```

---

## Usage

### 1. Scrape and Download Patent Files

Run `scraper.py` to:

* Scrape FTPS links for the given year (if not already saved)
* Download `index.xml`, patent XMLs, and image folders

```bash
python scraper.py --year 114
```

Creates a folder structure like:

```
114/
  └─ <ref_id>/
      ├─ _temp/index.xml
      ├─ <xml_name>/
      │   ├─ PatentIsuRegSpecXMLA/<doc_id>.xml
      │   └─ <mirrored image files>
      ├─ success_log.json
      └─ summary_log.csv
```

---

### 2. Generate Metadata

After downloading, run:

```bash
python generate_metadata.py --root 114
```

* Processes all subfolders under `114/`
* Outputs `<dataset_name>_metadata.csv` files with:

  * Application number
  * Image path
  * Representative flag
  * Chinese & English titles
  * Locarno classification code

---

### 3. Run the Entire Pipeline (Optional)

#### Usage:

```bash
chmod +x run_all.sh
./run_all.sh 114
```

---

## Notes

* Ensure `chromedriver` is compatible with your local Chrome version.
* `lftp` must be installed and available on your system.
* Progress is tracked via `success_log.json` and `summary_log.csv`.
* Supports partial resumption and avoids re-downloading already completed documents.

---

## License

MIT License
