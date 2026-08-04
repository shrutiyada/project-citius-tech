from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

# --- 1. Define the Strict Pydantic Schema ---

class Procedure(BaseModel):
    procedure_name: str = Field(description="Name or description of the medical procedure.")
    cpt_code: Optional[str] = Field(description="CPT code (if explicitly mentioned).", default=None)

class PriorAuthEntities(BaseModel):
    diagnoses: List[str] = Field(description="List of medical diagnoses or conditions found in the text.")
    procedures: List[Procedure] = Field(description="List of medical procedures and associated CPT codes.")

# --- 2. Define the Graph State ---

class AgentState(TypedDict):
    text: str
    extracted_entities: Optional[PriorAuthEntities]
    error: Optional[str]

# --- 3. Define the Entity Agent Workflow ---

class EntityExtractionAgent:
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o"):
        """
        Initializes the LangGraph agent for extracting Prior Auth entities.
        """
        if not openai_api_key:
            raise ValueError("OpenAI API key is required to initialize the EntityExtractionAgent.")
            
        print(f"[LANGGRAPH] Initializing Entity Extraction Agent with model '{model_name}'...")
        
        self.llm = ChatOpenAI(model=model_name, api_key=openai_api_key, temperature=0)
        self.structured_llm = self.llm.with_structured_output(PriorAuthEntities)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert medical coder and reviewer assisting in a prior authorization process. "
                       "Your task is to carefully extract all 'diagnoses' and 'procedures' (with CPT codes if available) "
                       "from the provided medical text. The text has been scrubbed for PHI, so you will see placeholders like <PERSON>. "
                       "Focus heavily on the procedures requested by the doctor. If no CPT code is found, leave it null."),
            ("user", "Extract entities from this text:\n\n{text}")
        ])
        
        self.graph = self._build_graph()

    def _extract_entities_node(self, state: AgentState) -> dict:
        text = state["text"]
        try:
            chain = self.prompt | self.structured_llm
            result: PriorAuthEntities = chain.invoke({"text": text})
            return {"extracted_entities": result, "error": None}
        except Exception as e:
            return {"error": str(e)}

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("extract", self._extract_entities_node)
        builder.set_entry_point("extract")
        builder.add_edge("extract", END)
        return builder.compile()

    def extract(self, text: str) -> dict:
        if not text.strip():
            return {"diagnoses": [], "procedures": []}
            
        initial_state = {"text": text, "extracted_entities": None, "error": None}
        final_state = self.graph.invoke(initial_state)
        
        if final_state.get("error"):
            print(f"[LANGGRAPH ERROR] Extraction failed: {final_state['error']}")
            return {"diagnoses": [], "procedures": [], "error": final_state["error"]}
            
        entities: PriorAuthEntities = final_state["extracted_entities"]
        return entities.dict()
