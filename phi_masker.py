from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from config import Config

class PHIMasker:
    def __init__(self):
        print("[PHI MASKER] Initializing Azure AI Language Service for PII/PHI detection...")
        endpoint = Config.AZURE_LANGUAGE_ENDPOINT
        key = Config.AZURE_LANGUAGE_KEY
        
        if not endpoint or not key:
            print("[PHI MASKER WARNING] AZURE_LANGUAGE_ENDPOINT or AZURE_LANGUAGE_KEY missing. Masking disabled.")
            self.client = None
        else:
            self.client = TextAnalyticsClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    def mask_text(self, text: str) -> str:
        if not text.strip() or not self.client: 
            return text
            
        try:
            # PII recognition (Healthcare PHI domain often requires specific models, but standard PII covers most PHI categories like Person, Date, PhoneNumber)
            response = self.client.recognize_pii_entities(documents=[text], language="en")[0]
            
            if response.is_error:
                print(f"[PHI MASKER ERROR] Azure returned an error: {response.error}")
                return text
                
            # Replace entities from the end of the string to the beginning so that offsets remain valid
            entities = sorted(response.entities, key=lambda x: x.offset, reverse=True)
            masked_text = text
            for entity in entities:
                # Replace the identified PHI string with its categorical tag (e.g., <PERSON>)
                masked_text = masked_text[:entity.offset] + f"<{entity.category}>" + masked_text[entity.offset + entity.length:]
                
            return masked_text
        except Exception as e:
            print(f"[PHI MASKER FATAL ERROR] {e}")
            return text
