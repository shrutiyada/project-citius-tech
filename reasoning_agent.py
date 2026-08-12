import json
import os
from difflib import SequenceMatcher
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import DefaultAzureCredential

class PriorAuthReasoningAgent:
    def __init__(self, endpoint: str, api_key: str = None, deployment_name: str = "gpt-4o", api_version: str = "2024-02-15-preview"):
        print(f"[MAF] Initializing Reasoning & Critique Agent with Azure OpenAI deployment '{deployment_name}'...")
        
        self.credential = DefaultAzureCredential()
        self.client = FoundryChatClient(
            project_endpoint=endpoint,
            credential=self.credential,
            model=deployment_name
        )
        
        # 1. Reasoning Prompt
        self.reasoning_sys_msg = (
            "You are a Medical Director conducting a strict prior authorization review. "
            "You will evaluate if the patient meets the medical necessity criteria. "
            "⚠️ CRITICAL INSTRUCTION: When extracting the 'criterion', you must pick complex, formal clinical thresholds from the Policy Data (e.g. 'Must have 6 months of conservative therapy', 'BMI > 35'). Ignore mundane administrative lines. "
            "⚠️ CRITICAL INSTRUCTION: When extracting 'evidence', you MUST quote the exact, verbatim text strictly from the PATIENT DATA that proves or disproves the criterion. DO NOT just copy the policy criterion. DO NOT paraphrase. DO NOT invent text. "
            "You MUST output valid JSON only matching this exact structure: "
            "{'decision': 'APPROVE/DENY/PEND', 'reasoning': 'summary string', 'criteria_matrix': [{'criterion': 'complex clinical threshold from policy', 'evidence': 'exact verbatim quote strictly from patient data', 'met': 'Yes/No', 'citation': '[Page X]'}]}"
        )
        self.reasoning_agent = Agent(client=self.client, instructions=self.reasoning_sys_msg)
        
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
        self.critique_agent = Agent(client=self.client, instructions=self.critique_sys_msg)
        
        # 3. CPT Deduce Prompt
        cpt_sys_msg = (
            "You are a medical coder. Review the patient's data below and output the exact CPT code of the "
            "procedure that is being requested for prior authorization. Output ONLY a valid JSON object matching "
            "this structure: {'cpt_code': 'the_code_as_string'}."
        )
        self.cpt_agent = Agent(client=self.client, instructions=cpt_sys_msg)

    async def _safe_run(self, agent, prompt: str) -> dict:
        result = await agent.run(prompt)
        result_str = str(result)
        if result_str.startswith("```json"):
            result_str = result_str.strip("```json").strip("```").strip()
        return json.loads(result_str)

    async def evaluate(self, patient_data: str, policy_data: str, target_cpt: str, human_feedback: str = None) -> dict:
        import json
        
        # 1. Extract and strip OCR polygons from patient_data to save tokens
        ocr_polygons = []
        try:
            patient_dict = json.loads(patient_data)
            ocr_polygons = patient_dict.pop("ocr_polygons", [])
            patient_data = json.dumps(patient_dict)
        except Exception:
            pass

        if not target_cpt:
            print("[MAF] Target CPT missing. Attempting to auto-deduce from Patient Data...")
            try:
                cpt_result = await self._safe_run(self.cpt_agent, f"Patient Data:\n{patient_data}")
                target_cpt = cpt_result.get("cpt_code", "UNKNOWN")
                print(f"[MAF] Auto-deduced CPT: {target_cpt}")
            except Exception as e:
                print(f"[MAF ERROR] Failed to deduce CPT: {e}")
                target_cpt = "UNKNOWN"
                
        context_payload = f"Target CPT: {target_cpt}\n\nPatient Data:\n{patient_data}\n\nPolicy Data:\n{policy_data}"
        
        if human_feedback:
            print("[MAF] Human-in-the-loop override detected.")
            reason_prompt = f"[CRITICAL OVERRIDE FROM HUMAN AUDITOR]: {human_feedback}\n\n{context_payload}"
            try:
                decision_json = await self._safe_run(self.reasoning_agent, reason_prompt)
                decision_json["audit_status"] = "MANUAL_OVERRIDE"
                decision_json["audit_feedback"] = "Decision updated by human auditor."
                return decision_json
            except Exception as e:
                return {"decision": "ERROR", "error": str(e)}

        max_attempts = 2
        current_critique_feedback = ""
        
        for attempt in range(1, max_attempts + 1):
            print(f"[MAF] Attempt {attempt}/{max_attempts}...")
            
            reason_prompt = context_payload
            if current_critique_feedback:
                reason_prompt += f"\n\n[PREVIOUS CRITIQUE FEEDBACK TO FIX]: {current_critique_feedback}"
                
            try:
                # Run Reasoning Agent
                decision_json = await self._safe_run(self.reasoning_agent, reason_prompt)
                
                # Formulate Critique Prompt
                critique_prompt = (
                    f"{context_payload}\n\n"
                    f"--- Proposed Decision to Review ---\n{json.dumps(decision_json, indent=2)}"
                )
                
                print("[MAF CRITIQUE AGENT] Auditing decision...")
                critique_json = await self._safe_run(self.critique_agent, critique_prompt)
                
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
                    
                    # True Bounding Box Algorithm Integration
                    if "criteria_matrix" in decision_json:
                        for row in decision_json["criteria_matrix"]:
                            evidence_str = row.get("evidence", "")
                            if evidence_str and evidence_str.strip():
                                best_box = None
                                best_ratio = 0.0
                                evidence_lower = evidence_str.lower()
                                
                                for poly in ocr_polygons:
                                    poly_text = poly.get("text", "").lower()
                                    # Exact substring match
                                    if poly_text in evidence_lower or evidence_lower in poly_text:
                                        ratio = 1.0
                                    else:
                                        # Fuzzy match overlap
                                        matcher = SequenceMatcher(None, evidence_lower, poly_text)
                                        ratio = matcher.quick_ratio()
                                        
                                    if ratio > best_ratio and ratio > 0.4:
                                        best_ratio = ratio
                                        p = poly.get("polygon", [])
                                        if len(p) >= 8:
                                            best_box = f"[{p[0]}, {p[1]}, {p[4]}, {p[5]}]"
                                        else:
                                            best_box = str(p)
                                            
                                row["bounding_box"] = best_box
                            else:
                                row["bounding_box"] = None
                                
                    return decision_json
                else:
                    print("[MAF CRITIQUE AGENT] Logic rejected. Sending back to Reasoning Agent...")
                    current_critique_feedback = critique_json.get("critique_feedback", "Fix the logic.")
                    
            except Exception as e:
                print(f"[MAF ERROR] Evaluation failed: {e}")
                return {"decision": "ERROR", "error": str(e)}
                
        return {"decision": "ERROR", "reasoning": "Failed to complete self-reflection loop."}
