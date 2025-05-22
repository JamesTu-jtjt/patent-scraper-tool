#!/bin/bash

# Exit on error
set -e

# Check and parse input
if [ -z "$1" ]; then
  echo "Usage: ./run_all.sh <year>"
  exit 1
fi

YEAR=$1
echo "[INFO] Starting full pipeline for year $YEAR"

# Step 1: Download XML + folder data
echo "[STEP 1] Downloading patent files for year $YEAR..."
python3 scraper.py --year "$YEAR"

# Step 3: Generate metadata CSVs
echo "[STEP 2] Generating metadata CSVs for year $YEAR..."
python3 generate_metadata.py --root "$YEAR"

echo "[DONE] All steps completed successfully for year $YEAR."
