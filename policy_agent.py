from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langchain_community.callbacks import get_openai_callback

class PolicyEntities(BaseModel):
    covered_cpt_codes: List[str] = Field(description="List of CPT codes explicitly covered by this policy.")
    medical_necessity_criteria: List[str] = Field(description="Specific criteria or conditions a patient must meet for the procedure to be approved.")
    exclusions: List[str] = Field(description="Conditions or situations explicitly excluded from coverage.")

class AgentState(TypedDict):
    text: str
    extracted_entities: Optional[PolicyEntities]
    error: Optional[str]

class PolicyEntityAgent:
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, api_key=openai_api_key, temperature=0)
        self.structured_llm = self.llm.with_structured_output(PolicyEntities)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert medical policy analyst. Your job is to read dense medical insurance policies "
                       "and extract the specific coverage rules. You must scan the entire document to find the 'Covered Indications', "
                       "'Medical Necessity Criteria', and 'Exclusions'. Pay close attention to age limits, required prior treatments, "
                       "and specific diagnosis requirements."),
            ("user", "Extract policy criteria from this document:\n\n{text}")
        ])
        self.graph = self._build_graph()

    def _extract_node(self, state: AgentState) -> dict:
        try:
            chain = self.prompt | self.structured_llm
            result: PolicyEntities = chain.invoke({"text": state["text"]})
            return {"extracted_entities": result, "error": None}
        except Exception as e:
            return {"error": str(e)}

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("extract", self._extract_node)
        builder.set_entry_point("extract")
        builder.add_edge("extract", END)
        return builder.compile()

    def extract(self, text: str) -> dict:
        if not text.strip(): return {"covered_cpt_codes": [], "medical_necessity_criteria": [], "exclusions": [], "llm_metrics": {}}
            
        with get_openai_callback() as cb:
            final_state = self.graph.invoke({"text": text, "extracted_entities": None, "error": None})
            metrics = {"total_tokens": cb.total_tokens, "total_cost_usd": cb.total_cost}
        
        if final_state.get("error"):
            return {"error": final_state["error"], "llm_metrics": metrics}
            
        result_dict = final_state["extracted_entities"].dict()
        result_dict["llm_metrics"] = metrics
        return result_dict
