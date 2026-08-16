import json
import os
import asyncio
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import DefaultAzureCredential

class PolicyEntityAgent:
    def __init__(self, endpoint: str, api_key: str = None, deployment_name: str = "gpt-4o", api_version: str = "2024-02-15-preview"):
        print(f"[MAF] Initializing Policy Agent with Azure OpenAI deployment '{deployment_name}'...")
        
        self.credential = DefaultAzureCredential()
        self.client = FoundryChatClient(
            project_endpoint=endpoint,
            credential=self.credential,
            model=deployment_name
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
        
        self.agent = Agent(client=self.client, instructions=self.system_message)

        self.validation_sys_msg = (
            "You are a Senior Medical Auditor validating extracted data. "
            "Review the extracted JSON against the provided Medical Policy Document chunk. "
            "1. Ensure no criteria or exclusions were hallucinated or incorrectly summarized. "
            "2. Ensure EVERY citation explicitly matches a [Page X] marker that actually exists in the text. "
            "If the extraction is 100% accurate, output 'PASS'. "
            "If there are errors or hallucinations, output 'FAIL' along with specific feedback on what to fix. "
            "You MUST output valid JSON only matching this structure: {'status': 'PASS/FAIL', 'feedback': 'string'}"
        )
        self.validation_agent = Agent(client=self.client, instructions=self.validation_sys_msg)

    async def _extract_chunk(self, chunk_text: str, chunk_index: int) -> dict:
        context_prompt = f"Medical Policy Document Chunk {chunk_index}:\n{chunk_text}"
        max_attempts = 2
        feedback = ""
        
        for attempt in range(1, max_attempts + 1):
            prompt = context_prompt
            if feedback:
                prompt += f"\n\n[PREVIOUS VALIDATION FEEDBACK TO FIX]: {feedback}"
                
            try:
                result = await self.agent.run(prompt)
                result_str = str(result)
                if result_str.startswith("```json"):
                    result_str = result_str.strip("```json").strip("```").strip()
                parsed_json = json.loads(result_str)
                
                validation_prompt = f"{context_prompt}\n\n--- Extracted Data to Audit ---\n{json.dumps(parsed_json, indent=2)}"
                val_result = await self.validation_agent.run(validation_prompt)
                val_str = str(val_result)
                if val_str.startswith("```json"):
                    val_str = val_str.strip("```json").strip("```").strip()
                val_json = json.loads(val_str)
                
                if val_json.get("status") == "PASS" or attempt == max_attempts:
                    parsed_json["audit_status"] = val_json.get("status", "PASS")
                    parsed_json["audit_feedback"] = val_json.get("feedback")
                    return parsed_json
                else:
                    feedback = val_json.get("feedback", "Fix hallucinations.")
                    
            except Exception as e:
                print(f"[MAF ERROR] Chunk {chunk_index} failed: {e}")
                return {"medical_necessity_criteria": [], "exclusions": [], "audit_status": "FAIL", "audit_feedback": str(e)}
                
        return {"medical_necessity_criteria": [], "exclusions": [], "audit_status": "FAIL"}

    async def extract(self, text: str) -> dict:
        if not text.strip():
            return {"medical_necessity_criteria": [], "exclusions": [], "audit_status": "PASS"}
            
        chunk_size = 6000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        print(f"[MAF] Splitting Policy Document into {len(chunks)} parallel chunks...")
        tasks = [self._extract_chunk(chunk, i) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks)
        
        merged = {"medical_necessity_criteria": [], "exclusions": [], "audit_status": "PASS"}
        for r in results:
            merged["medical_necessity_criteria"].extend(r.get("medical_necessity_criteria", []))
            merged["exclusions"].extend(r.get("exclusions", []))
            if r.get("audit_status") == "FAIL":
                merged["audit_status"] = "FAIL"
                
        return merged
