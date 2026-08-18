import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    # 1. Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_CONTAINER_NAME_PATIENT = os.getenv("AZURE_CONTAINER_NAME_PATIENT", "patient-records")
    AZURE_CONTAINER_NAME_POLICY = os.getenv("AZURE_CONTAINER_NAME_POLICY", "medical-policies")
    
    # 2. Azure Document Intelligence
    AZURE_DOC_INTEL_ENDPOINT = os.getenv("AZURE_DOC_INTEL_ENDPOINT", "")
    AZURE_DOC_INTEL_KEY = os.getenv("AZURE_DOC_INTEL_KEY", "")
    AZURE_DOC_INTEL_MODEL = os.getenv("AZURE_DOC_INTEL_MODEL", "prebuilt-layout")

    # 3. Azure OpenAI (Azure AI Foundry)
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")
    
    # 5. Azure AI Language (PHI Masking)
    AZURE_LANGUAGE_ENDPOINT = os.getenv("AZURE_LANGUAGE_ENDPOINT", "")
    AZURE_LANGUAGE_KEY = os.getenv("AZURE_LANGUAGE_KEY", "")
    
    # 4. Azure AI Search (Knowledge Base)
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
    AZURE_SEARCH_INDEX_PATIENT = os.getenv("AZURE_SEARCH_INDEX_PATIENT", "patient-auth-index")
    AZURE_SEARCH_INDEX_POLICY = os.getenv("AZURE_SEARCH_INDEX_POLICY", "medical-policy-index")

    OUTPUT_DIR = Path("output")
    
    @classmethod
    def validate_all(cls) -> bool:
        missing = []
        if not cls.AZURE_STORAGE_CONNECTION_STRING: missing.append("AZURE_STORAGE_CONNECTION_STRING")
        if not cls.AZURE_DOC_INTEL_ENDPOINT: missing.append("AZURE_DOC_INTEL_ENDPOINT")
        if not cls.AZURE_DOC_INTEL_KEY: missing.append("AZURE_DOC_INTEL_KEY")
        if not cls.AZURE_OPENAI_ENDPOINT: missing.append("AZURE_OPENAI_ENDPOINT")
        if not cls.AZURE_OPENAI_DEPLOYMENT_NAME: missing.append("AZURE_OPENAI_DEPLOYMENT_NAME")
        if not cls.AZURE_SEARCH_ENDPOINT: missing.append("AZURE_SEARCH_ENDPOINT")
        if not cls.AZURE_SEARCH_KEY: missing.append("AZURE_SEARCH_KEY")
        
        if missing:
            print(f"[FATAL] Missing required environment variables:\n - " + "\n - ".join(missing))
            return False
        return True
