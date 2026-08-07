import json
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatPromptExecutionSettings

class PriorAuthReasoningAgent:
    def __init__(self, endpoint: str, api_key: str, deployment_name: str, api_version: str = "2024-02-15-preview"):
        print(f"[SEMANTIC KERNEL] Initializing Reasoning & Critique Agent with Azure OpenAI deployment '{deployment_name}'...")
        
        self.kernel = Kernel()
        chat_service = AzureChatCompletion(
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.kernel.add_service(chat_service)
        
        # 1. Reasoning Prompt
        self.reasoning_sys_msg = (
            "You are a Medical Director conducting a prior authorization review. "
            "You will evaluate if the patient meets the medical necessity criteria. "
            "If they meet all criteria, APPROVE. If they fail criteria, DENY. "
            "You MUST output valid JSON only: "
            "{'decision': 'APPROVE/DENY/PEND', 'reasoning': 'string', 'matched_criteria': 'string'}"
        )
        
        # 2. Critique Prompt
        self.critique_sys_msg = (
            "You are a Senior Medical Auditor reviewing a Prior Auth decision. "
            "Review the decision against the patient data and policy data. "
            "If the decision logic is sound and misses no exclusions, output 'PASS'. "
            "If the decision logic is flawed, output 'FAIL' along with a critique explaining what they missed. "
            "You MUST output valid JSON only: "
            "{'status': 'PASS/FAIL', 'critique_feedback': 'string or null'}"
        )
        
        self.execution_settings = OpenAIChatPromptExecutionSettings(
            temperature=0.0,
            response_format={"type": "json_object"}
        )

    async def evaluate(self, patient_data: str, policy_data: str, target_cpt: str) -> dict:
        context_payload = f"Target CPT: {target_cpt}\n\nPatient Data:\n{patient_data}\n\nPolicy Data:\n{policy_data}"
        
        max_attempts = 2
        current_critique_feedback = ""
        
        for attempt in range(1, max_attempts + 1):
            print(f"[REASONING AGENT] Attempt {attempt}/{max_attempts}...")
            
            # Formulate Reasoning Prompt (include past critique if any)
            reason_prompt = f"{self.reasoning_sys_msg}\n\n{context_payload}"
            if current_critique_feedback:
                reason_prompt += f"\n\n[PREVIOUS CRITIQUE FEEDBACK TO FIX]: {current_critique_feedback}"
                
            try:
                # Run Reasoning Agent
                reason_result = await self.kernel.invoke_prompt(
                    prompt=reason_prompt,
                    plugin_name="DecisionEngine",
                    function_name="Reasoning",
                    settings=self.execution_settings
                )
                decision_json = json.loads(str(reason_result))
                
                # Formulate Critique Prompt
                critique_prompt = (
                    f"{self.critique_sys_msg}\n\n"
                    f"{context_payload}\n\n"
                    f"--- Proposed Decision to Review ---\n{json.dumps(decision_json, indent=2)}"
                )
                
                print("[CRITIQUE AGENT] Auditing decision...")
                critique_result = await self.kernel.invoke_prompt(
                    prompt=critique_prompt,
                    plugin_name="DecisionEngine",
                    function_name="Critique",
                    settings=self.execution_settings
                )
                critique_json = json.loads(str(critique_result))
                
                # Check status
                if critique_json.get("status") == "PASS" or attempt == max_attempts:
                    decision_json["audit_status"] = critique_json.get("status", "PASS")
                    decision_json["audit_feedback"] = critique_json.get("critique_feedback")
                    return decision_json
                else:
                    print("[CRITIQUE AGENT] Logic rejected. Sending back to Reasoning Agent...")
                    current_critique_feedback = critique_json.get("critique_feedback", "Fix the logic.")
                    
            except Exception as e:
                print(f"[SEMANTIC KERNEL ERROR] Evaluation failed: {e}")
                return {"decision": "ERROR", "error": str(e)}
                
        return {"decision": "ERROR", "reasoning": "Failed to complete self-reflection loop."}
