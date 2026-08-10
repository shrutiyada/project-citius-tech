from typing import Dict, Any
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

class AzureDocIntelligenceProcessor:
    def __init__(self, endpoint: str, key: str, model_id: str = "prebuilt-layout"):
        self.model_id = model_id
        self.client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    def process_pdf_url(self, pdf_url: str, filename: str) -> Dict[str, Any]:
        request = AnalyzeDocumentRequest(url_source=pdf_url)
        poller = self.client.begin_analyze_document(model_id=self.model_id, body=request)
        result = poller.result()
        
        full_text = ""
        if hasattr(result, "pages"):
            for page in result.pages:
                full_text += f"\n\n--- [Page {page.page_number}] ---\n"
                if hasattr(page, "lines"):
                    for line in page.lines:
                        full_text += line.content + "\n"
        else:
            full_text = result.content if hasattr(result, "content") else ""
            
        return {"filename": filename, "full_content": full_text.strip()}
