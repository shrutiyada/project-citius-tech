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
        
        # Initialize MAF Agent
        self.agent = Agent(
            client=self.client,
            instructions=self.system_message
        )

        self.validation_sys_msg = (
            "You are a Senior Medical Auditor validating extracted data. "
            "Review the extracted JSON against the provided Patient Record. "
            "1. Ensure no diagnoses or procedures were hallucinated. "
            "2. Ensure EVERY citation explicitly matches a [Page X] marker that actually exists in the text. "
            "If the extraction is 100% accurate, output 'PASS'. "
            "If there are errors or hallucinations, output 'FAIL' along with specific feedback on what to fix. "
            "You MUST output valid JSON only matching this structure: {'status': 'PASS/FAIL', 'feedback': 'string'}"
        )
        self.validation_agent = Agent(client=self.client, instructions=self.validation_sys_msg)

    async def extract(self, text: str) -> dict:
        if not text.strip():
            return {"diagnoses": [], "procedures": []}
            
        context_prompt = f"Patient Record:\n{text}"
        
        max_attempts = 2
        feedback = ""
        
        for attempt in range(1, max_attempts + 1):
            prompt = context_prompt
            if feedback:
                prompt += f"\n\n[PREVIOUS VALIDATION FEEDBACK TO FIX]: {feedback}"
                
            try:
                # 1. Extraction
                result = await self.agent.run(prompt)
                result_str = str(result)
                if result_str.startswith("```json"):
                    result_str = result_str.strip("```json").strip("```").strip()
                parsed_json = json.loads(result_str)
                
                # 2. Validation
                validation_prompt = f"{context_prompt}\n\n--- Extracted Data to Audit ---\n{json.dumps(parsed_json, indent=2)}"
                val_result = await self.validation_agent.run(validation_prompt)
                val_str = str(val_result)
                if val_str.startswith("```json"):
                    val_str = val_str.strip("```json").strip("```").strip()
                val_json = json.loads(val_str)
                
                if val_json.get("status") == "PASS" or attempt == max_attempts:
                    parsed_json["llm_metrics"] = {"total_tokens": 0, "total_cost_usd": 0.0}
                    parsed_json["audit_status"] = val_json.get("status", "PASS")
                    parsed_json["audit_feedback"] = val_json.get("feedback")
                    return parsed_json
                else:
                    feedback = val_json.get("feedback", "Fix hallucinations.")
                    
            except Exception as e:
                print(f"[MAF ERROR] Patient Extraction failed: {e}")
                return {"error": str(e), "diagnoses": [], "procedures": [], "llm_metrics": {}}
                
        return {"diagnoses": [], "procedures": []}
