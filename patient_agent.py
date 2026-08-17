import json
import os
import asyncio
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import DefaultAzureCredential

class PatientEntityAgent:
    def __init__(self, endpoint: str, api_key: str = None, deployment_name: str = "gpt-4o", api_version: str = "2024-02-15-preview"):
        print(f"[MAF] Initializing Patient Agent with Azure OpenAI deployment '{deployment_name}'...")
        
        self.credential = DefaultAzureCredential()
        self.client = FoundryChatClient(
            project_endpoint=endpoint,
            credential=self.credential,
            model=deployment_name
        )
        
        self.system_message = (
            "You are an expert medical coder. Extract all 'diagnoses' and 'procedures' (with CPT codes if available) "
            "from the provided medical text. Focus heavily on the procedures requested by the doctor. "
            "The text contains [Page X] markers.\n\n"
            "⚠️ CRITICAL SAFETY WARNING ON CITATIONS ⚠️\n"
            "You MUST include the exact page citation for EVERY extracted entity.\n"
            "DO NOT guess or invent page numbers. You must locate the exact [Page X] marker that immediately precedes the text you are quoting.\n"
            "Failure to provide accurate citations is a critical safety violation.\n\n"
            "The text has been scrubbed for PHI (you will see placeholders like <PERSON>).\n"
            "You MUST output valid JSON only, matching this structure:\n"
            "{\n"
            "  'diagnoses': [{'diagnosis': 'string', 'citations': ['[Page X]']}],\n"
            "  'procedures': [{'procedure_name': 'string', 'cpt_code': 'string or null', 'citations': ['[Page X]']}]\n"
            "}"
        )
        
        self.agent = Agent(client=self.client, instructions=self.system_message)

    async def _extract_chunk(self, chunk_text: str, chunk_index: int) -> dict:
        context_prompt = f"Patient Record Chunk {chunk_index}:\n{chunk_text}"
        try:
            result = await self.agent.run(context_prompt)
            result_str = str(result)
            if result_str.startswith("```json"):
                result_str = result_str.strip("```json").strip("```").strip()
            parsed_json = json.loads(result_str)
            return parsed_json
        except Exception as e:
            print(f"[MAF ERROR] Chunk {chunk_index} failed: {e}")
            return {"diagnoses": [], "procedures": []}

    async def extract(self, text: str) -> dict:
        if not text.strip():
            return {"diagnoses": [], "procedures": []}
            
        chunk_size = 6000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        print(f"[MAF] Splitting Patient Record into {len(chunks)} parallel chunks (No Chunk Validation)...")
        tasks = [self._extract_chunk(chunk, i) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks)
        
        merged = {"diagnoses": [], "procedures": []}
        for r in results:
            merged["diagnoses"].extend(r.get("diagnoses", []))
            merged["procedures"].extend(r.get("procedures", []))
                
        return merged
