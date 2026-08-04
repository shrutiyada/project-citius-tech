import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

from config import Config
from azure_blob_handler import AzureBlobHandler
from azure_doc_intelligence_processor import AzureDocIntelligenceProcessor

def save_results_to_json(data: List[Dict[str, Any]], output_path: Path) -> None:
    """Save aggregated Azure Document Intelligence data to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"\n[SUCCESS] Extracted JSON output saved to: '{output_path.resolve()}'")

def run_doc_intelligence_pipeline():
    parser = argparse.ArgumentParser(description="Extract text & tables from Azure Blob Storage PDFs using Azure Document Intelligence.")
    parser.add_argument("--folder", type=str, help="Override default Azure Blob folder prefix", default=None)
    parser.add_argument("--output", type=str, help="Override output JSON filepath", default="output/azure_doc_intel_text.json")
    args = parser.parse_args()

    # Validate settings
    if not Config.validate_azure_blob():
        print("[FATAL] Missing Azure Blob Storage credentials.")
        sys.exit(1)
        
    if not Config.validate_doc_intelligence():
        print("[FATAL] Missing Azure Document Intelligence credentials in .env file.")
        sys.exit(1)

    folder_prefix = args.folder if args.folder is not None else Config.AZURE_BLOB_FOLDER_PREFIX
    output_path = Path(args.output)

    # Initialize Azure Handlers
    try:
        blob_handler = AzureBlobHandler(
            connection_string=Config.AZURE_STORAGE_CONNECTION_STRING,
            container_name=Config.AZURE_CONTAINER_NAME
        )
        
        doc_intel_processor = AzureDocIntelligenceProcessor(
            endpoint=Config.AZURE_DOC_INTEL_ENDPOINT,
            key=Config.AZURE_DOC_INTEL_KEY,
            model_id=Config.AZURE_DOC_INTEL_MODEL
        )
    except Exception as e:
        print(f"[FATAL] Initialization error: {e}")
        sys.exit(1)

    # 1. Fetch PDF list from Azure Blob Storage
    try:
        pdf_blobs = blob_handler.list_pdf_blobs(folder_prefix=folder_prefix)
    except Exception as e:
        print(f"[FATAL] Failed to fetch PDF list from Azure Blob Storage: {e}")
        sys.exit(1)

    if not pdf_blobs:
        print(f"[INFO] No PDF blobs found under prefix '{folder_prefix}'. Exiting.")
        return

    all_results: List[Dict[str, Any]] = []

    # 2. Process each PDF blob using Azure Document Intelligence
    for idx, blob_name in enumerate(pdf_blobs, start=1):
        print(f"\n--- [{idx}/{len(pdf_blobs)}] Analyzing with Azure Document Intelligence: {blob_name} ---")
        try:
            pdf_bytes = blob_handler.download_blob_bytes(blob_name)
            result = doc_intel_processor.process_pdf_bytes(pdf_bytes, filename=blob_name)
            all_results.append(result)
        except Exception as e:
            print(f"[ERROR] Skipping '{blob_name}' due to error: {e}")

    # 3. Export to JSON
    save_results_to_json(all_results, output_path)

if __name__ == "__main__":
    run_doc_intelligence_pipeline()
