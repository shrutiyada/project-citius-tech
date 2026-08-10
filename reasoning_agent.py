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
            "You will evaluate if the patient meets the medical necessity criteria line-by-line. "
            "You MUST output valid JSON only matching this exact structure: "
            "{'decision': 'APPROVE/DENY/PEND', 'reasoning': 'summary string', 'criteria_matrix': [{'criterion': 'string', 'evidence': 'exact quote from patient data', 'met': 'Yes/No', 'citation': '[Page X]'}]}"
        )
        
        # 2. Critique Prompt
        self.critique_sys_msg = (
            "You are a Senior Medical Auditor reviewing a Prior Auth decision. "
            "Review the decision against the patient data and policy data. "
            "If the decision logic is sound and misses no exclusions, output 'PASS'. "
            "If the decision logic is flawed, output 'FAIL' along with a critique. "
            "You MUST also calculate standard RAGAS metrics (1-100) for the decision quality. "
            "You MUST output valid JSON only matching this exact structure: "
            "{'status': 'PASS/FAIL', 'critique_feedback': 'string or null', 'faithfulness_score': 95, 'relevance_score': 95, 'precision_score': 95, 'recall_score': 95}"
        )
        
        self.execution_settings = OpenAIChatPromptExecutionSettings(
            temperature=0.0,
            response_format={"type": "json_object"}
        )

    async def evaluate(self, patient_data: str, policy_data: str, target_cpt: str, human_feedback: str = None) -> dict:
        if not target_cpt:
            print("[REASONING AGENT] Target CPT missing. Attempting to auto-deduce from Patient Data...")
            cpt_prompt = (
                "You are a medical coder. Review the patient's data below and output the exact CPT code of the "
                "procedure that is being requested for prior authorization. Output ONLY a valid JSON object matching "
                "this structure: {'cpt_code': 'the_code_as_string'}.\n\nPatient Data:\n" + patient_data
            )
            try:
                cpt_result = await self.kernel.invoke_prompt(
                    prompt=cpt_prompt, plugin_name="DecisionEngine", function_name="DeduceCPT", settings=self.execution_settings
                )
                target_cpt = json.loads(str(cpt_result)).get("cpt_code", "UNKNOWN")
                print(f"[REASONING AGENT] Auto-deduced CPT: {target_cpt}")
            except Exception as e:
                print(f"[REASONING AGENT ERROR] Failed to deduce CPT: {e}")
                target_cpt = "UNKNOWN"
                
        context_payload = f"Target CPT: {target_cpt}\n\nPatient Data:\n{patient_data}\n\nPolicy Data:\n{policy_data}"
        
        if human_feedback:
            print("[REASONING AGENT] Human-in-the-loop override detected.")
            reason_prompt = f"{self.reasoning_sys_msg}\n\n[CRITICAL OVERRIDE FROM HUMAN AUDITOR]: {human_feedback}\n\n{context_payload}"
            try:
                result = await self.kernel.invoke_prompt(prompt=reason_prompt, plugin_name="DecisionEngine", function_name="ReasoningOverride", settings=self.execution_settings)
                decision_json = json.loads(str(result))
                decision_json["audit_status"] = "MANUAL_OVERRIDE"
                decision_json["audit_feedback"] = "Decision updated by human auditor."
                return decision_json
            except Exception as e:
                return {"decision": "ERROR", "error": str(e)}

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
                    decision_json["ragas_metrics"] = {
                        "faithfulness": critique_json.get("faithfulness_score", 90),
                        "relevance": critique_json.get("relevance_score", 90),
                        "precision": critique_json.get("precision_score", 90),
                        "recall": critique_json.get("recall_score", 90)
                    }
                    
                    # Bounding Box Stub Integration
                    if "criteria_matrix" in decision_json:
                        for row in decision_json["criteria_matrix"]:
                            if row.get("evidence") and row.get("citation"):
                                row["bounding_box"] = "[120, 345, 450, 520]" # Stub for OCR Polygon matching
                            else:
                                row["bounding_box"] = None
                                
                    return decision_json
                else:
                    print("[CRITIQUE AGENT] Logic rejected. Sending back to Reasoning Agent...")
                    current_critique_feedback = critique_json.get("critique_feedback", "Fix the logic.")
                    
            except Exception as e:
                print(f"[SEMANTIC KERNEL ERROR] Evaluation failed: {e}")
                return {"decision": "ERROR", "error": str(e)}
                
        return {"decision": "ERROR", "reasoning": "Failed to complete self-reflection loop."}
