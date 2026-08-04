import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "")
    AZURE_BLOB_FOLDER_PREFIX = os.getenv("AZURE_BLOB_FOLDER_PREFIX", "")
    
    # Azure Document Intelligence
    AZURE_DOC_INTEL_ENDPOINT = os.getenv("AZURE_DOC_INTEL_ENDPOINT", "")
    AZURE_DOC_INTEL_KEY = os.getenv("AZURE_DOC_INTEL_KEY", "")
    AZURE_DOC_INTEL_MODEL = os.getenv("AZURE_DOC_INTEL_MODEL", "prebuilt-layout")

    # Tesseract OCR
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
    OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "eng")
    OCR_DPI = int(os.getenv("OCR_DPI", "300"))
    
    OUTPUT_JSON_PATH = Path(os.getenv("OUTPUT_JSON_PATH", "output/extracted_text.json"))
    
    @classmethod
    def validate_azure_blob(cls) -> bool:
        """Validate required Azure Blob Storage parameters."""
        missing = []
        if not cls.AZURE_STORAGE_CONNECTION_STRING:
            missing.append("AZURE_STORAGE_CONNECTION_STRING")
        if not cls.AZURE_CONTAINER_NAME:
            missing.append("AZURE_CONTAINER_NAME")
            
        if missing:
            print(f"[WARNING] Missing Azure Blob environment variables: {', '.join(missing)}")
            return False
        return True

    @classmethod
    def validate_doc_intelligence(cls) -> bool:
        """Validate required Azure Document Intelligence parameters."""
        missing = []
        if not cls.AZURE_DOC_INTEL_ENDPOINT:
            missing.append("AZURE_DOC_INTEL_ENDPOINT")
        if not cls.AZURE_DOC_INTEL_KEY:
            missing.append("AZURE_DOC_INTEL_KEY")
            
        if missing:
            print(f"[WARNING] Missing Azure Document Intelligence environment variables: {', '.join(missing)}")
            return False
        return True
