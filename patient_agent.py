from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langchain_community.callbacks import get_openai_callback

class Procedure(BaseModel):
    procedure_name: str = Field(description="Name or description of the medical procedure.")
    cpt_code: Optional[str] = Field(description="CPT code (if explicitly mentioned).", default=None)

class PatientEntities(BaseModel):
    diagnoses: List[str] = Field(description="List of medical diagnoses or conditions found in the text.")
    procedures: List[Procedure] = Field(description="List of medical procedures and associated CPT codes requested.")

class AgentState(TypedDict):
    text: str
    extracted_entities: Optional[PatientEntities]
    error: Optional[str]

class PatientEntityAgent:
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, api_key=openai_api_key, temperature=0)
        self.structured_llm = self.llm.with_structured_output(PatientEntities)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert medical coder. Extract all 'diagnoses' and 'procedures' (with CPT codes if available) "
                       "from the provided medical text. Focus heavily on the procedures requested by the doctor. "
                       "The text has been scrubbed for PHI (you will see placeholders like <PERSON>)."),
            ("user", "Extract entities from this patient record:\n\n{text}")
        ])
        self.graph = self._build_graph()

    def _extract_node(self, state: AgentState) -> dict:
        try:
            chain = self.prompt | self.structured_llm
            result: PatientEntities = chain.invoke({"text": state["text"]})
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
        if not text.strip(): return {"diagnoses": [], "procedures": [], "llm_metrics": {}}
            
        with get_openai_callback() as cb:
            final_state = self.graph.invoke({"text": text, "extracted_entities": None, "error": None})
            metrics = {"total_tokens": cb.total_tokens, "total_cost_usd": cb.total_cost}
        
        if final_state.get("error"):
            return {"error": final_state["error"], "llm_metrics": metrics}
            
        result_dict = final_state["extracted_entities"].dict()
        result_dict["llm_metrics"] = metrics
        return result_dict
