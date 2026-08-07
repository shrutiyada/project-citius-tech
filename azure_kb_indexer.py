import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.core.exceptions import AzureError

class AzureKBIndexer:
    def __init__(self, endpoint: str, key: str, index_name: str):
        if not endpoint or not key or not index_name:
            raise ValueError("Azure Search credentials missing.")
        self.client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))

    def index_document(self, doc_id: str, text_content: str, entities: dict):
        safe_id = "".join(c if c.isalnum() else "_" for c in doc_id)
        doc = {"id": safe_id, "content": text_content, "entities_metadata": json.dumps(entities)}
        try:
            self.client.upload_documents(documents=[doc])
            print(f"[AZURE SEARCH] Indexed '{safe_id}'.")
        except AzureError as e:
            print(f"[AZURE SEARCH ERROR] {e}")

    def get_document(self, doc_id: str) -> dict:
        safe_id = "".join(c if c.isalnum() else "_" for c in doc_id)
        try:
            return self.client.get_document(key=safe_id)
        except AzureError:
            return None
