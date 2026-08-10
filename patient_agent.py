import json
from pydantic import BaseModel
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.prompt_template import PromptTemplateConfig

class PatientEntityAgent:
    def __init__(self, endpoint: str, api_key: str, deployment_name: str, api_version: str = "2024-02-15-preview"):
        print(f"[SEMANTIC KERNEL] Initializing Patient Agent with Azure OpenAI deployment '{deployment_name}'...")
        
        # Initialize the Kernel
        self.kernel = Kernel()
        
        # Add the Azure OpenAI Chat Completion service
        chat_service = AzureChatCompletion(
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.kernel.add_service(chat_service)
        
        # Define the system prompt
        self.system_message = (
            "You are an expert medical coder. Extract all 'diagnoses' and 'procedures' (with CPT codes if available) "
            "from the provided medical text. Focus heavily on the procedures requested by the doctor. "
            "The text contains [Page X] markers. You MUST include exact page citations for every extracted entity. "
            "The text has been scrubbed for PHI (you will see placeholders like <PERSON>).\n"
            "You MUST output valid JSON only, matching this structure:\n"
            "{\n"
            "  'diagnoses': [{'diagnosis': 'string', 'citations': ['[Page X]']}],\n"
            "  'procedures': [{'procedure_name': 'string', 'cpt_code': 'string or null', 'citations': ['[Page X]']}]\n"
            "}"
        )
        
        # Configure execution settings for JSON output
        self.execution_settings = OpenAIChatPromptExecutionSettings(
            temperature=0.0,
            response_format={"type": "json_object"}
        )

    async def extract(self, text: str) -> dict:
        if not text.strip():
            return {"diagnoses": [], "procedures": []}
            
        prompt = f"{self.system_message}\n\nPatient Record:\n{text}"
        
        try:
            # Execute the prompt
            result = await self.kernel.invoke_prompt(
                prompt=prompt,
                plugin_name="PatientExtraction",
                function_name="ExtractEntities",
                settings=self.execution_settings
            )
            
            # Parse the JSON result
            result_str = str(result)
            parsed_json = json.loads(result_str)
            
            # Semantic Kernel Python doesn't expose raw token usage natively in invoke_prompt yet in the same way,
            # so we return a placeholder for metrics to keep compatibility with the API.
            parsed_json["llm_metrics"] = {"total_tokens": 0, "total_cost_usd": 0.0}
            
            return parsed_json
            
        except Exception as e:
            print(f"[SEMANTIC KERNEL ERROR] Extraction failed: {e}")
            return {"error": str(e), "diagnoses": [], "procedures": [], "llm_metrics": {}}
