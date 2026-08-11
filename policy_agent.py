import json
import os
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import DefaultAzureCredential

class PolicyEntityAgent:
    def __init__(self, endpoint: str, api_key: str = None, deployment_name: str = "gpt-4o", api_version: str = "2024-02-15-preview"):
        print(f"[MAF] Initializing Policy Agent with Azure OpenAI deployment '{deployment_name}'...")
        
        # Initialize MAF Client with Entra ID
        self.credential = DefaultAzureCredential()
        self.client = FoundryChatClient(
            endpoint=endpoint,
            credential=self.credential,
            deployment_name=deployment_name,
            api_version=api_version
        )
        
        self.system_message = (
            "You are an expert medical policy analyst. Your job is to read dense medical insurance policies "
            "and extract the specific coverage rules. You must scan the entire document to find the "
            "'Medical Necessity Criteria' and 'Exclusions'. Do NOT extract diagnoses or CPT codes.\n"
            "The text contains [Page X] markers.\n\n"
            "⚠️ CRITICAL SAFETY WARNING ON CITATIONS ⚠️\n"
            "You MUST include the exact page citation for EVERY extracted rule.\n"
            "DO NOT guess or invent page numbers. You must locate the exact [Page X] marker that immediately precedes the text you are quoting.\n"
            "Failure to provide accurate citations is a critical safety violation.\n\n"
            "You MUST output valid JSON only, matching this structure:\n"
            "{\n"
            "  'medical_necessity_criteria': [{'criterion': 'string', 'citations': ['[Page X]']}],\n"
            "  'exclusions': [{'exclusion': 'string', 'citations': ['[Page X]']}]\n"
            "}"
        )
        
        # Initialize MAF Agent
        self.agent = Agent(
            client=self.client,
            system_message=self.system_message
        )

    async def extract(self, text: str) -> dict:
        if not text.strip():
            return {"covered_cpt_codes": [], "medical_necessity_criteria": [], "exclusions": []}
            
        prompt = f"Medical Policy Document:\n{text}"
        
        try:
            # Execute via MAF
            result = await self.agent.run(prompt)
            
            result_str = str(result)
            if result_str.startswith("```json"):
                result_str = result_str.strip("```json").strip("```").strip()
                
            parsed_json = json.loads(result_str)
            parsed_json["llm_metrics"] = {"total_tokens": 0, "total_cost_usd": 0.0}
            
            return parsed_json
            
        except Exception as e:
            print(f"[MAF ERROR] Policy Extraction failed: {e}")
            return {"error": str(e), "medical_necessity_criteria": [], "exclusions": [], "llm_metrics": {}}
