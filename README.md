# Azure Blob PDF Processing: Tesseract OCR vs. Azure Document Intelligence

Python pipeline to list & download scanned PDF files from an Azure Blob Storage folder, extract page text, lines, tables, and structured data, and output the results as a JSON file.

Supports **two processing engines**:
1. **Tesseract OCR (Local & Free)**
2. **Azure Document Intelligence (AI Cloud)**

---

## 1. Environment Setup

### Install Dependencies
```bash
cd /Users/shrutiyadav/.gemini/antigravity/scratch/azure_pdf_ocr
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure `.env` Credentials
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Set variables inside `.env`:
```env
# 1. Azure Blob Storage Credentials
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_CONTAINER_NAME=your_container
AZURE_BLOB_FOLDER_PREFIX=axure_blob_folder/

# 2. Azure Document Intelligence (Optional - for AI OCR)
AZURE_DOC_INTEL_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOC_INTEL_KEY=your_secret_key
AZURE_DOC_INTEL_MODEL=prebuilt-layout

# 3. Tesseract Settings (Local OCR)
OCR_LANGUAGE=eng
OCR_DPI=300
```

---

## 2. How to Run

### Option A: Run Azure Document Intelligence (Recommended for AI Accuracy & Tables)
```bash
python main_azure_doc_intel.py
```

### Option B: Run Tesseract OCR (Free / Local)
```bash
python main.py
```

### Option C: Test a Local PDF File
```bash
# Test local PDF using Azure Document Intelligence
python test_azure_doc_intel.py path/to/sample.pdf

# Test local PDF using Tesseract OCR
python test_local_ocr.py path/to/sample.pdf
```

---

## 3. How the Output JSON is Saved

Both scripts generate structured JSON files saved under the `output/` directory (e.g. `output/azure_doc_intel_text.json` or `output/extracted_text.json`).

### Azure Document Intelligence JSON Structure:
```json
[
    {
        "filename": "axure_blob_folder/scanned_invoice.pdf",
        "model_used": "prebuilt-layout",
        "full_content": "Invoice #1042\nDate: 2026-08-04...",
        "total_pages": 1,
        "pages": [
            {
                "page_number": 1,
                "lines": [
                    { "text": "Invoice #1042" },
                    { "text": "Date: 2026-08-04" }
                ]
            }
        ],
        "tables": [
            {
                "table_id": 1,
                "row_count": 3,
                "column_count": 2,
                "cells": [
                    { "row_index": 0, "column_index": 0, "content": "Item" },
                    { "row_index": 0, "column_index": 1, "content": "Price" },
                    { "row_index": 1, "column_index": 0, "content": "Service Fee" },
                    { "row_index": 1, "column_index": 1, "content": "$150.00" }
                ]
            }
        ],
        "key_value_pairs": [
            { "key": "Invoice Number", "value": "1042" },
            { "key": "Total Due", "value": "$150.00" }
        ]
    }
]
```
