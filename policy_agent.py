import json
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatPromptExecutionSettings

class PolicyEntityAgent:
    def __init__(self, endpoint: str, api_key: str, deployment_name: str, api_version: str = "2024-02-15-preview"):
        print(f"[SEMANTIC KERNEL] Initializing Policy Agent with Azure OpenAI deployment '{deployment_name}'...")
        
        self.kernel = Kernel()
        chat_service = AzureChatCompletion(
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.kernel.add_service(chat_service)
        
        self.system_message = (
            "You are an expert medical policy analyst. Your job is to read dense medical insurance policies "
            "and extract the specific coverage rules. You must scan the entire document to find the 'Covered Indications', "
            "'Medical Necessity Criteria', and 'Exclusions'.\n"
            "You MUST output valid JSON only, matching this structure: "
            "{'covered_cpt_codes': ['string'], 'medical_necessity_criteria': ['string'], 'exclusions': ['string']}"
        )
        
        self.execution_settings = OpenAIChatPromptExecutionSettings(
            temperature=0.0,
            response_format={"type": "json_object"}
        )

    async def extract(self, text: str) -> dict:
        if not text.strip():
            return {"covered_cpt_codes": [], "medical_necessity_criteria": [], "exclusions": []}
            
        prompt = f"{self.system_message}\n\nMedical Policy Document:\n{text}"
        
        try:
            result = await self.kernel.invoke_prompt(
                prompt=prompt,
                plugin_name="PolicyExtraction",
                function_name="ExtractRules",
                settings=self.execution_settings
            )
            
            parsed_json = json.loads(str(result))
            parsed_json["llm_metrics"] = {"total_tokens": 0, "total_cost_usd": 0.0}
            return parsed_json
            
        except Exception as e:
            print(f"[SEMANTIC KERNEL ERROR] Extraction failed: {e}")
            return {"error": str(e), "covered_cpt_codes": [], "medical_necessity_criteria": [], "exclusions": [], "llm_metrics": {}}
