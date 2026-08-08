import datetime
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import AzureError

class AzureBlobHandler:
    def __init__(self, connection_string: str):
        if not connection_string:
            raise ValueError("Connection string must be provided.")
            
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.account_name = self.blob_service_client.account_name
        
        # Extract AccountKey for SAS generation
        parts = connection_string.split(";")
        self.account_key = None
        for part in parts:
            if part.startswith("AccountKey="):
                self.account_key = part.replace("AccountKey=", "")
                break

        if not self.account_key:
            raise ValueError("Could not parse AccountKey from connection string.")

    def upload_blob(self, container_name: str, blob_name: str, data: bytes) -> str:
        """Uploads raw bytes to a specific container and returns the blob name."""
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            # Create container if it doesn't exist
            if not container_client.exists():
                container_client.create_container()
                
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(data, overwrite=True)
            print(f"[AZURE BLOB] Successfully uploaded '{blob_name}' to '{container_name}'.")
            return blob_name
        except AzureError as e:
            print(f"[AZURE BLOB ERROR] Failed to upload blob: {e}")
            raise

    def generate_sas_url(self, container_name: str, blob_name: str, expiry_hours: int = 1) -> str:
        """Generates a SAS URL for a specific blob in a specific container."""
        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=self.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=expiry_hours)
        )
        
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        return f"{blob_client.url}?{sas_token}"
