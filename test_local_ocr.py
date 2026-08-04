import json
import argparse
from pathlib import Path
from ocr_processor import OCRProcessor

def test_local_pdf(pdf_path: str, output_path: str = "output/local_test_result.json"):
    """
    Utility script to test OCR processing on a local PDF file.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"[ERROR] Local PDF file not found at: '{pdf_path}'")
        return

    with open(pdf_file, "rb") as f:
        pdf_bytes = f.read()

    ocr_processor = OCRProcessor()
    result = ocr_processor.process_pdf_bytes(pdf_bytes, filename=pdf_file.name)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump([result], f, indent=4, ensure_ascii=False)

    print(f"\n[SUCCESS] Local test completed. Output saved to '{out_file.resolve()}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Tesseract OCR extraction on a local PDF file.")
    parser.add_argument("pdf_path", type=str, help="Path to local PDF file")
    parser.add_argument("--output", type=str, default="output/local_test_result.json", help="Path to save result JSON")
    args = parser.parse_args()

    test_local_pdf(args.pdf_path, args.output)
