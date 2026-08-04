import io
from typing import Dict, Any, List, Optional
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult

class AzureDocIntelligenceProcessor:
    def __init__(self, endpoint: str, key: str, model_id: str = "prebuilt-layout"):
        """
        Initialize Azure Document Intelligence Client.
        
        :param endpoint: Azure Document Intelligence Endpoint URL
        :param key: Azure Document Intelligence Subscription/API Key
        :param model_id: Prebuilt model identifier ('prebuilt-layout' or 'prebuilt-read')
        """
        if not endpoint or not key:
            raise ValueError("Azure Document Intelligence endpoint and key are required.")

        self.endpoint = endpoint
        self.key = key
        self.model_id = model_id
        
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

    def process_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze PDF byte stream with Azure Document Intelligence.
        
        :param pdf_bytes: Binary content of PDF file
        :param filename: Document identifier/filename
        :return: Formatted dictionary containing extracted text, pages, and tables
        """
        print(f"[DOC INTEL] Analyzing '{filename}' using model '{self.model_id}'...")
        
        poller = self.client.begin_analyze_document(
            model_id=self.model_id,
            body=pdf_bytes,
            content_type="application/pdf"
        )
        result: AnalyzeResult = poller.result()
        
        return self._format_result(result, filename)

    def process_pdf_url(self, pdf_url: str, filename: str) -> Dict[str, Any]:
        """
        Analyze PDF directly from an Azure Blob URL without downloading locally.
        
        :param pdf_url: Accessible URL (or SAS URL) of the PDF blob
        :param filename: Document identifier/filename
        :return: Formatted dictionary containing extracted text, pages, and tables
        """
        print(f"[DOC INTEL] Analyzing remote URL '{filename}' using model '{self.model_id}'...")
        
        request = AnalyzeDocumentRequest(url_source=pdf_url)
        poller = self.client.begin_analyze_document(
            model_id=self.model_id,
            body=request
        )
        result: AnalyzeResult = poller.result()
        
        return self._format_result(result, filename)

    def _format_result(self, result: AnalyzeResult, filename: str) -> Dict[str, Any]:
        """Format AnalyzeResult into structured JSON dictionary."""
        formatted_output: Dict[str, Any] = {
            "filename": filename,
            "model_used": self.model_id,
            "full_content": result.content if hasattr(result, "content") else "",
            "total_pages": len(result.pages) if result.pages else 0,
            "pages": [],
            "tables": [],
            "key_value_pairs": []
        }

        # 1. Page-by-page extraction
        if result.pages:
            for page in result.pages:
                page_info = {
                    "page_number": page.page_number,
                    "width": page.width,
                    "height": page.height,
                    "unit": page.unit,
                    "lines": []
                }
                
                if page.lines:
                    for line in page.lines:
                        page_info["lines"].append({
                            "text": line.content,
                        })
                
                formatted_output["pages"].append(page_info)

        # 2. Extract Structured Tables (if prebuilt-layout model is used)
        if hasattr(result, "tables") and result.tables:
            for table_idx, table in enumerate(result.tables, start=1):
                table_info = {
                    "table_id": table_idx,
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": []
                }
                for cell in table.cells:
                    table_info["cells"].append({
                        "row_index": cell.row_index,
                        "column_index": cell.column_index,
                        "content": cell.content,
                        "kind": cell.kind if hasattr(cell, "kind") else "content"
                    })
                formatted_output["tables"].append(table_info)

        # 3. Extract Key-Value Pairs
        if hasattr(result, "key_value_pairs") and result.key_value_pairs:
            for kv in result.key_value_pairs:
                if kv.key and kv.value:
                    formatted_output["key_value_pairs"].append({
                        "key": kv.key.content,
                        "value": kv.value.content
                    })

        print(f"[DOC INTEL] Processed '{filename}': {formatted_output['total_pages']} page(s), {len(formatted_output['tables'])} table(s).")
        return formatted_output
