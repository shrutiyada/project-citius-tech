from typing import TypedDict
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langchain_community.callbacks import get_openai_callback

class AuthDecision(BaseModel):
    decision: str = Field(description="Must be exactly 'APPROVE', 'DENY', or 'PEND'.")
    reasoning: str = Field(description="Detailed explanation of why the decision was made based on comparing patient data to policy criteria.")
    matched_criteria: str = Field(description="The specific policy criteria that drove the decision.")

class ReasoningState(TypedDict):
    patient_data: str
    policy_data: str
    target_cpt: str
    result: AuthDecision
    error: str

class PriorAuthReasoningAgent:
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, api_key=openai_api_key, temperature=0)
        self.structured_llm = self.llm.with_structured_output(AuthDecision)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Medical Director conducting a prior authorization review. "
                       "You will be given extracted 'Patient Data' and 'Medical Policy Criteria' for a specific requested CPT code. "
                       "Your job is to evaluate if the patient meets the medical necessity criteria. "
                       "If they meet all criteria, APPROVE. If they explicitly violate an exclusion or fail criteria, DENY. "
                       "If there is not enough information to make a decision, PEND the request for more info."),
            ("user", "Target CPT Code: {target_cpt}\n\n--- Patient Data ---\n{patient_data}\n\n--- Policy Data ---\n{policy_data}")
        ])
        self.graph = self._build_graph()

    def _reasoning_node(self, state: ReasoningState) -> dict:
        try:
            chain = self.prompt | self.structured_llm
            result: AuthDecision = chain.invoke({
                "target_cpt": state["target_cpt"],
                "patient_data": state["patient_data"],
                "policy_data": state["policy_data"]
            })
            return {"result": result, "error": None}
        except Exception as e:
            return {"error": str(e)}

    def _build_graph(self):
        builder = StateGraph(ReasoningState)
        builder.add_node("evaluate", self._reasoning_node)
        builder.set_entry_point("evaluate")
        builder.add_edge("evaluate", END)
        return builder.compile()

    def evaluate(self, patient_data: str, policy_data: str, target_cpt: str) -> dict:
        with get_openai_callback() as cb:
            final_state = self.graph.invoke({
                "patient_data": patient_data, 
                "policy_data": policy_data, 
                "target_cpt": target_cpt,
                "result": None,
                "error": None
            })
            metrics = {"total_tokens": cb.total_tokens, "total_cost_usd": cb.total_cost}
        
        if final_state.get("error"):
            return {"error": final_state["error"], "llm_metrics": metrics}
            
        result_dict = final_state["result"].dict()
        result_dict["llm_metrics"] = metrics
        return result_dict
