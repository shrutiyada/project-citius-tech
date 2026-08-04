import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

from config import Config
from azure_blob_handler import AzureBlobHandler
from ocr_processor import OCRProcessor

def save_results_to_json(data: List[Dict[str, Any]], output_path: Path) -> None:
    """Save aggregated OCR extraction data to a formatted JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"\n[SUCCESS] Extracted OCR data saved to JSON file: '{output_path.resolve()}'")

def run_pipeline():
    parser = argparse.ArgumentParser(description="Extract text from scanned PDFs in Azure Blob Storage using Tesseract OCR.")
    parser.add_argument("--folder", type=str, help="Override default Azure Blob folder prefix", default=None)
    parser.add_argument("--output", type=str, help="Override output JSON filepath", default=None)
    args = parser.parse_args()

    # Validate settings
    if not Config.validate():
        sys.exit(1)

    folder_prefix = args.folder if args.folder is not None else Config.AZURE_BLOB_FOLDER_PREFIX
    output_path = Path(args.output) if args.output else Config.OUTPUT_JSON_PATH

    # Initialize Azure Handler & OCR Processor
    try:
        azure_handler = AzureBlobHandler(
            connection_string=Config.AZURE_STORAGE_CONNECTION_STRING,
            container_name=Config.AZURE_CONTAINER_NAME
        )
    except Exception as e:
        print(f"[FATAL] Failed to initialize Azure Blob Handler: {e}")
        sys.exit(1)

    ocr_processor = OCRProcessor(
        tesseract_cmd=Config.TESSERACT_CMD if Config.TESSERACT_CMD else None,
        lang=Config.OCR_LANGUAGE,
        dpi=Config.OCR_DPI
    )

    # 1. Fetch PDF list from Azure Blob Storage
    try:
        pdf_blobs = azure_handler.list_pdf_blobs(folder_prefix=folder_prefix)
    except Exception as e:
        print(f"[FATAL] Failed to fetch PDF list from Azure: {e}")
        sys.exit(1)

    if not pdf_blobs:
        print(f"[INFO] No PDF blobs found in container '{Config.AZURE_CONTAINER_NAME}' under prefix '{folder_prefix}'. Exiting.")
        return

    all_results: List[Dict[str, Any]] = []

    # 2. Process each PDF blob
    for idx, blob_name in enumerate(pdf_blobs, start=1):
        print(f"\n--- [{idx}/{len(pdf_blobs)}] Processing: {blob_name} ---")
        try:
            pdf_bytes = azure_handler.download_blob_bytes(blob_name)
            ocr_result = ocr_processor.process_pdf_bytes(pdf_bytes, filename=blob_name)
            all_results.append(ocr_result)
        except Exception as e:
            print(f"[ERROR] Skipping '{blob_name}' due to error: {e}")

    # 3. Export to JSON
    save_results_to_json(all_results, output_path)

if __name__ == "__main__":
    run_pipeline()
