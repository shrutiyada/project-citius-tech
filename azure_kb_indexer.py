import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchableField
from azure.core.exceptions import AzureError, ResourceNotFoundError

class AzureKBIndexer:
    def __init__(self, endpoint: str, key: str, index_name: str):
        if not endpoint or not key or not index_name:
            raise ValueError("Azure Search credentials missing.")
            
        self.endpoint = endpoint
        self.key = key
        self.index_name = index_name
        self.credential = AzureKeyCredential(key)
        self.client = SearchClient(endpoint=endpoint, index_name=index_name, credential=self.credential)
        
        # Ensure the index exists
        self._ensure_index_exists()

    def _ensure_index_exists(self):
        index_client = SearchIndexClient(endpoint=self.endpoint, credential=self.credential)
        try:
            index_client.get_index(self.index_name)
        except ResourceNotFoundError:
            print(f"[AZURE SEARCH] Index '{self.index_name}' not found. Creating it now...")
            fields = [
                SimpleField(name="id", type="Edm.String", key=True),
                SearchableField(name="content", type="Edm.String"),
                SimpleField(name="entities_metadata", type="Edm.String")
            ]
            index = SearchIndex(name=self.index_name, fields=fields)
            index_client.create_index(index)
            print(f"[AZURE SEARCH] Successfully created index '{self.index_name}'.")

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
