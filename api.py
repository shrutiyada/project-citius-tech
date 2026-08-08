from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List
import uvicorn
import json
from config import Config
from azure_blob_handler import AzureBlobHandler
from azure_doc_intelligence_processor import AzureDocIntelligenceProcessor
from phi_masker import PHIMasker
from patient_agent import PatientEntityAgent
from policy_agent import PolicyEntityAgent
from reasoning_agent import PriorAuthReasoningAgent
from chat_agent import ChatAgent
from azure_kb_indexer import AzureKBIndexer

app = FastAPI(title="Prior Auth Decision Engine API")

# Initialize shared resources
if not Config.validate_all():
    raise RuntimeError("Missing configuration.")

blob_handler = AzureBlobHandler(Config.AZURE_STORAGE_CONNECTION_STRING)
doc_intel = AzureDocIntelligenceProcessor(Config.AZURE_DOC_INTEL_ENDPOINT, Config.AZURE_DOC_INTEL_KEY)
phi_masker = PHIMasker()

# Initialize Agents with Azure OpenAI
patient_agent = PatientEntityAgent(
    Config.AZURE_OPENAI_ENDPOINT, Config.AZURE_OPENAI_API_KEY, 
    Config.AZURE_OPENAI_DEPLOYMENT_NAME, Config.AZURE_OPENAI_API_VERSION
)
policy_agent = PolicyEntityAgent(
    Config.AZURE_OPENAI_ENDPOINT, Config.AZURE_OPENAI_API_KEY, 
    Config.AZURE_OPENAI_DEPLOYMENT_NAME, Config.AZURE_OPENAI_API_VERSION
)
reasoning_agent = PriorAuthReasoningAgent(
    Config.AZURE_OPENAI_ENDPOINT, Config.AZURE_OPENAI_API_KEY, 
    Config.AZURE_OPENAI_DEPLOYMENT_NAME, Config.AZURE_OPENAI_API_VERSION
)
chat_agent = ChatAgent(
    Config.AZURE_OPENAI_ENDPOINT, Config.AZURE_OPENAI_API_KEY, 
    Config.AZURE_OPENAI_DEPLOYMENT_NAME, Config.AZURE_OPENAI_API_VERSION
)

patient_kb = AzureKBIndexer(Config.AZURE_SEARCH_ENDPOINT, Config.AZURE_SEARCH_KEY, Config.AZURE_SEARCH_INDEX_PATIENT)
policy_kb = AzureKBIndexer(Config.AZURE_SEARCH_ENDPOINT, Config.AZURE_SEARCH_KEY, Config.AZURE_SEARCH_INDEX_POLICY)

@app.post("/upload/patient")
async def upload_patient(patient_id: str = Form(...), files: List[UploadFile] = File(...)):
    combined_raw_text = ""
    uploaded_files = []
    
    for file in files:
        # 1. Upload to Blob
        file_bytes = await file.read()
        blob_name = f"{patient_id}_{file.filename}"
        blob_handler.upload_blob(Config.AZURE_CONTAINER_NAME_PATIENT, blob_name, file_bytes)
        
        # 2. Extract OCR
        sas_url = blob_handler.generate_sas_url(Config.AZURE_CONTAINER_NAME_PATIENT, blob_name)
        ocr_result = doc_intel.process_pdf_url(sas_url, blob_name)
        combined_raw_text += f"\n--- Document: {file.filename} ---\n{ocr_result['full_content']}\n"
        uploaded_files.append(blob_name)
        
    # 3. Mask PHI & Extract Entities (Fix: added await)
    masked_text = phi_masker.mask_text(combined_raw_text)
    entities = await patient_agent.extract(masked_text)
    
    # 4. Save to DB under the single Patient ID
    patient_kb.index_document(patient_id, masked_text, entities)
    return {"message": f"Patient {patient_id} indexed with {len(files)} files.", "entities": entities, "files": uploaded_files}

@app.post("/upload/policy")
async def upload_policy(policy_id: str = Form(...), file: UploadFile = File(...)):
    file_bytes = await file.read()
    blob_name = f"{policy_id}_{file.filename}"
    blob_handler.upload_blob(Config.AZURE_CONTAINER_NAME_POLICY, blob_name, file_bytes)
    
    sas_url = blob_handler.generate_sas_url(Config.AZURE_CONTAINER_NAME_POLICY, blob_name)
    raw_text = doc_intel.process_pdf_url(sas_url, blob_name)["full_content"]
    
    # No PHI Masking for public policies (Fix: added await)
    entities = await policy_agent.extract(raw_text)
    policy_kb.index_document(policy_id, raw_text, entities)
    return {"message": f"Policy {policy_id} indexed.", "entities": entities}

@app.post("/evaluate")
async def evaluate_prior_auth(patient_id: str, policy_id: str, target_cpt: str):
    patient_doc = patient_kb.get_document(patient_id)
    policy_doc = policy_kb.get_document(policy_id)
    
    if not patient_doc or not policy_doc:
        raise HTTPException(status_code=404, detail="Document not found in KB.")
        
    patient_data = patient_doc.get("entities_metadata", "")
    policy_data = policy_doc.get("entities_metadata", "")
    
    # Ensure it's a string even if stored as parsed dict depending on kb indexer version
    if isinstance(patient_data, str) and patient_data.startswith("{"):
        pass # Already JSON string
    else:
        patient_data = json.dumps(patient_data)
        
    if isinstance(policy_data, str) and policy_data.startswith("{"):
        pass
    else:
        policy_data = json.dumps(policy_data)
    
    decision = await reasoning_agent.evaluate(patient_data, policy_data, target_cpt)
    return {"decision": decision}

from pydantic import BaseModel
class ChatRequest(BaseModel):
    query: str
    patient_id: str
    policy_id: str

@app.post("/chat")
async def chat_assistant(request: ChatRequest):
    patient_doc = patient_kb.get_document(request.patient_id)
    policy_doc = policy_kb.get_document(request.policy_id)
    
    patient_data = patient_doc.get("entities_metadata", "") if patient_doc else "No patient data found."
    policy_data = policy_doc.get("entities_metadata", "") if policy_doc else "No policy data found."
    
    if not isinstance(patient_data, str): patient_data = json.dumps(patient_data)
    if not isinstance(policy_data, str): policy_data = json.dumps(policy_data)
    
    response = await chat_agent.answer_question(request.query, patient_data, policy_data)
    return {"response": response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
