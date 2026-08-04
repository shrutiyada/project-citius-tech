import io
from typing import List, Generator, Tuple
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
from azure.core.exceptions import AzureError

class AzureBlobHandler:
    def __init__(self, connection_string: str, container_name: str):
        """
        Initialize the Azure Blob Storage handler.
        
        :param connection_string: Azure Storage Connection String
        :param container_name: Name of the target Azure container
        """
        if not connection_string or not container_name:
            raise ValueError("Connection string and container name must be provided.")
            
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)

    def list_pdf_blobs(self, folder_prefix: str = "") -> List[str]:
        """
        List all PDF blobs in the container under an optional folder prefix.
        
        :param folder_prefix: Path prefix inside the container (e.g., 'scanned_pdfs/')
        :return: List of blob names ending with '.pdf'
        """
        try:
            print(f"[AZURE] Listing PDF blobs under prefix: '{folder_prefix}'...")
            blobs = self.container_client.list_blobs(name_starts_with=folder_prefix)
            pdf_blobs = [blob.name for blob in blobs if blob.name.lower().endswith('.pdf')]
            print(f"[AZURE] Found {len(pdf_blobs)} PDF file(s).")
            return pdf_blobs
        except AzureError as e:
            print(f"[AZURE ERROR] Failed to list blobs: {e}")
            raise

    def download_blob_bytes(self, blob_name: str) -> bytes:
        """
        Download a blob directly into memory as bytes.
        
        :param blob_name: Name/path of the blob in the container
        :return: Byte content of the downloaded blob
        """
        try:
            print(f"[AZURE] Downloading blob: '{blob_name}'...")
            blob_client = self.container_client.get_blob_client(blob_name)
            download_stream = blob_client.download_blob()
            content = download_stream.readall()
            print(f"[AZURE] Downloaded '{blob_name}' ({len(content)} bytes).")
            return content
        except AzureError as e:
            print(f"[AZURE ERROR] Failed to download blob '{blob_name}': {e}")
            raise
