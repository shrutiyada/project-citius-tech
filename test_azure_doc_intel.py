import json
import sys
import argparse
from pathlib import Path
from config import Config
from azure_doc_intelligence_processor import AzureDocIntelligenceProcessor

def test_local_doc_intel(pdf_path: str, output_path: str = "output/local_azure_doc_intel_test.json"):
    """
    Test Azure Document Intelligence on a local PDF file.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"[ERROR] Local PDF file not found at: '{pdf_path}'")
        return

    if not Config.validate_doc_intelligence():
        print("[FATAL] Missing AZURE_DOC_INTEL_ENDPOINT and AZURE_DOC_INTEL_KEY in .env file.")
        return

    with open(pdf_file, "rb") as f:
        pdf_bytes = f.read()

    doc_intel_processor = AzureDocIntelligenceProcessor(
        endpoint=Config.AZURE_DOC_INTEL_ENDPOINT,
        key=Config.AZURE_DOC_INTEL_KEY,
        model_id=Config.AZURE_DOC_INTEL_MODEL
    )
    
    result = doc_intel_processor.process_pdf_bytes(pdf_bytes, filename=pdf_file.name)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump([result], f, indent=4, ensure_ascii=False)

    print(f"\n[SUCCESS] Local Azure Document Intelligence test complete! Output saved to: '{out_file.resolve()}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Azure Document Intelligence on a local PDF file.")
    parser.add_argument("pdf_path", type=str, help="Path to local PDF file")
    parser.add_argument("--output", type=str, default="output/local_azure_doc_intel_test.json", help="Path to save output JSON")
    args = parser.parse_args()

    test_local_doc_intel(args.pdf_path, args.output)
