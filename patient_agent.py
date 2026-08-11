import json
import os
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import DefaultAzureCredential

class PatientEntityAgent:
    def __init__(self, endpoint: str, api_key: str = None, deployment_name: str = "gpt-4o", api_version: str = "2024-02-15-preview"):
        print(f"[MAF] Initializing Patient Agent with Azure OpenAI deployment '{deployment_name}'...")
        
        # Initialize MAF Client with Entra ID
        self.credential = DefaultAzureCredential()
        self.client = FoundryChatClient(
            endpoint=endpoint,
            credential=self.credential,
            deployment_name=deployment_name,
            api_version=api_version
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
        
        # Initialize MAF Agent
        self.agent = Agent(
            client=self.client,
            system_message=self.system_message
        )

    async def extract(self, text: str) -> dict:
        if not text.strip():
            return {"diagnoses": [], "procedures": []}
            
        prompt = f"Patient Record:\n{text}"
        
        try:
            # Execute via MAF
            result = await self.agent.run(prompt)
            
            result_str = str(result)
            # Handle potential markdown code blocks in the output
            if result_str.startswith("```json"):
                result_str = result_str.strip("```json").strip("```").strip()
                
            parsed_json = json.loads(result_str)
            parsed_json["llm_metrics"] = {"total_tokens": 0, "total_cost_usd": 0.0}
            
            return parsed_json
            
        except Exception as e:
            print(f"[MAF ERROR] Patient Extraction failed: {e}")
            return {"error": str(e), "diagnoses": [], "procedures": [], "llm_metrics": {}}
