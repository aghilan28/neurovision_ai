#!/bin/bash
# Download a targeted subset of CHB-MIT during Docker build.
# Only downloads EDF files that contain seizures + a few background files.
# Total download: ~400MB (vs 40GB full dataset).

set -e

OUTPUT_DIR="${1:-/app/data/chbmit}"
mkdir -p "$OUTPUT_DIR"

BASE="https://physionet.org/files/chbmit/1.0.0"

# Patients to download (5 patients with diverse seizure patterns)
PATIENTS="chb01 chb03 chb05 chb10 chb23"

for PATIENT in $PATIENTS; do
    echo "=== Downloading $PATIENT ==="
    mkdir -p "$OUTPUT_DIR/$PATIENT"
    
    # Download summary
    curl -s "$BASE/$PATIENT/${PATIENT}-summary.txt" -o "$OUTPUT_DIR/$PATIENT/${PATIENT}-summary.txt"
    
    # Parse summary to find seizure files
    SEIZURE_FILES=$(grep -B1 "Number of Seizures in File: [1-9]" "$OUTPUT_DIR/$PATIENT/${PATIENT}-summary.txt" | \
                    grep "File Name:" | sed 's/File Name: //' | tr -d '\r')
    
    # Also get 2 background files per patient
    ALL_FILES=$(grep "File Name:" "$OUTPUT_DIR/$PATIENT/${PATIENT}-summary.txt" | \
                sed 's/File Name: //' | tr -d '\r')
    BG_COUNT=0
    
    for FILE in $ALL_FILES; do
        IS_SEIZURE=$(echo "$SEIZURE_FILES" | grep -c "$FILE" || true)
        
        if [ "$IS_SEIZURE" -gt 0 ]; then
            echo "  Downloading $FILE (SEIZURE)..."
            curl -s --max-time 120 "$BASE/$PATIENT/$FILE" -o "$OUTPUT_DIR/$PATIENT/$FILE" || echo "  FAILED: $FILE"
        elif [ "$BG_COUNT" -lt 2 ]; then
            echo "  Downloading $FILE (background)..."
            curl -s --max-time 120 "$BASE/$PATIENT/$FILE" -o "$OUTPUT_DIR/$PATIENT/$FILE" || echo "  FAILED: $FILE"
            BG_COUNT=$((BG_COUNT + 1))
        fi
    done
done

echo "=== CHB-MIT subset downloaded ==="
du -sh "$OUTPUT_DIR"
find "$OUTPUT_DIR" -name "*.edf" | wc -l
echo "EDF files downloaded"
