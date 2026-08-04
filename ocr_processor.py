import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
from typing import Dict, Any, List, Optional

class OCRProcessor:
    def __init__(self, tesseract_cmd: Optional[str] = None, lang: str = "eng", dpi: int = 300):
        """
        Initialize the OCR Processor.
        
        :param tesseract_cmd: Path to tesseract executable if not in PATH environment variable.
        :param lang: OCR language (e.g. 'eng', 'fra', 'deu', etc.)
        :param dpi: Rendering resolution DPI for PDF page rasterization (default: 300)
        """
        self.lang = lang
        self.dpi = dpi

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        else:
            # Common Homebrew path check on macOS if standard tesseract is not found in PATH
            custom_brew_path = "/opt/homebrew/bin/tesseract"
            if os.path.exists(custom_brew_path):
                pytesseract.pytesseract.tesseract_cmd = custom_brew_path

    def process_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Process PDF byte content, render pages to high-resolution images, and run Tesseract OCR.
        
        :param pdf_bytes: Raw bytes of the PDF file
        :param filename: Name or identifier of the PDF
        :return: Dictionary containing extracted metadata and page-level OCR text
        """
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(pdf_document)
        
        results: Dict[str, Any] = {
            "filename": filename,
            "total_pages": total_pages,
            "pages": []
        }

        print(f"[OCR] Processing '{filename}' ({total_pages} page(s))...")

        for page_num in range(total_pages):
            page = pdf_document.load_page(page_num)
            
            # Render page to high-DPI pixmap
            pix = page.get_pixmap(dpi=self.dpi)
            
            # Convert PyMuPDF pixmap to PIL Image
            mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            if mode == "RGBA":
                img = img.convert("RGB")

            # Run Tesseract OCR on the page image
            try:
                extracted_text = pytesseract.image_to_string(img, lang=self.lang)
            except Exception as e:
                print(f"[OCR ERROR] Failed on page {page_num + 1} of '{filename}': {e}")
                extracted_text = f"[OCR ERROR: {str(e)}]"

            page_data = {
                "page_number": page_num + 1,
                "text": extracted_text.strip(),
                "character_count": len(extracted_text.strip())
            }
            
            results["pages"].append(page_data)
            print(f"[OCR] Processed Page {page_num + 1}/{total_pages} ({page_data['character_count']} chars)")

        pdf_document.close()
        return results
