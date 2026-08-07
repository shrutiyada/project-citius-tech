from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn
from config import Config
from azure_blob_handler import AzureBlobHandler
from azure_doc_intelligence_processor import AzureDocIntelligenceProcessor
from phi_masker import PHIMasker
from patient_agent import PatientEntityAgent
from policy_agent import PolicyEntityAgent
from reasoning_agent import PriorAuthReasoningAgent
from azure_kb_indexer import AzureKBIndexer

app = FastAPI(title="Prior Auth Decision Engine API")

# Initialize shared resources
if not Config.validate_all():
    raise RuntimeError("Missing configuration.")

blob_handler = AzureBlobHandler(Config.AZURE_STORAGE_CONNECTION_STRING)
doc_intel = AzureDocIntelligenceProcessor(Config.AZURE_DOC_INTEL_ENDPOINT, Config.AZURE_DOC_INTEL_KEY)
phi_masker = PHIMasker()
patient_agent = PatientEntityAgent(Config.OPENAI_API_KEY)
policy_agent = PolicyEntityAgent(Config.OPENAI_API_KEY)
reasoning_agent = PriorAuthReasoningAgent(Config.OPENAI_API_KEY)

patient_kb = AzureKBIndexer(Config.AZURE_SEARCH_ENDPOINT, Config.AZURE_SEARCH_KEY, Config.AZURE_SEARCH_INDEX_PATIENT)
policy_kb = AzureKBIndexer(Config.AZURE_SEARCH_ENDPOINT, Config.AZURE_SEARCH_KEY, Config.AZURE_SEARCH_INDEX_POLICY)

@app.post("/upload/patient")
async def upload_patient(file: UploadFile = File(...)):
    # 1. Upload to Blob
    file_bytes = await file.read()
    blob_name = file.filename
    blob_handler.upload_blob(Config.AZURE_CONTAINER_NAME_PATIENT, blob_name, file_bytes)
    
    # 2. Extract OCR
    sas_url = blob_handler.generate_sas_url(Config.AZURE_CONTAINER_NAME_PATIENT, blob_name)
    raw_text = doc_intel.process_pdf_url(sas_url, blob_name)["full_content"]
    
    # 3. Mask PHI & Extract Entities
    masked_text = phi_masker.mask_text(raw_text)
    entities = patient_agent.extract(masked_text)
    
    # 4. Save to DB
    patient_kb.index_document(blob_name, masked_text, entities)
    return {"message": f"Patient {blob_name} indexed.", "entities": entities}

@app.post("/upload/policy")
async def upload_policy(file: UploadFile = File(...)):
    file_bytes = await file.read()
    blob_name = file.filename
    blob_handler.upload_blob(Config.AZURE_CONTAINER_NAME_POLICY, blob_name, file_bytes)
    
    sas_url = blob_handler.generate_sas_url(Config.AZURE_CONTAINER_NAME_POLICY, blob_name)
    raw_text = doc_intel.process_pdf_url(sas_url, blob_name)["full_content"]
    
    # No PHI Masking for public policies
    entities = policy_agent.extract(raw_text)
    policy_kb.index_document(blob_name, raw_text, entities)
    return {"message": f"Policy {blob_name} indexed.", "entities": entities}

@app.post("/evaluate")
async def evaluate_prior_auth(patient_id: str, policy_id: str, target_cpt: str):
    # Fetch from Knowledge Bases
    patient_doc = patient_kb.get_document(patient_id)
    policy_doc = policy_kb.get_document(policy_id)
    
    if not patient_doc or not policy_doc:
        raise HTTPException(status_code=404, detail="Document not found in KB.")
        
    patient_data = patient_doc.get("entities_metadata", "")
    policy_data = policy_doc.get("entities_metadata", "")
    
    decision = reasoning_agent.evaluate(patient_data, policy_data, target_cpt)
    return {"decision": decision}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
