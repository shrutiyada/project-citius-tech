from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uvicorn
import json
import time
import os
from config import Config
from azure_blob_handler import AzureBlobHandler
from azure_doc_intelligence_processor import AzureDocIntelligenceProcessor
from phi_masker import PHIMasker
from patient_agent import PatientEntityAgent
from policy_agent import PolicyEntityAgent
from reasoning_agent import PriorAuthReasoningAgent
from chat_agent import ChatAgent
from azure_kb_indexer import AzureKBIndexer
from openai import AzureOpenAI
import database

app = FastAPI(title="Prior Auth Decision Engine API")

# Prevent browser caching of the React index.html
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Initialize shared resources
if not Config.validate_all():
    raise RuntimeError("Missing configuration.")

# Initialize Local Database for State Management
database.init_db()

blob_handler = AzureBlobHandler(Config.AZURE_STORAGE_CONNECTION_STRING)
doc_intel = AzureDocIntelligenceProcessor(Config.AZURE_DOC_INTEL_ENDPOINT, Config.AZURE_DOC_INTEL_KEY)
phi_masker = PHIMasker()

gpt_client = AzureOpenAI(
    api_key=Config.AZURE_OPENAI_API_KEY,
    api_version=Config.AZURE_OPENAI_API_VERSION,
    azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
)

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


async def background_process_patient(patient_id: str, files_data: list):
    print(f"[BACKGROUND] Processing Patient {patient_id} with {len(files_data)} files...")
    
    all_text = ""
    for idx, f in enumerate(files_data):
        file_bytes = f["bytes"]
        filename = f["filename"]
        blob_name = f"patient_{patient_id}_{idx}_{filename}"
        
        # Upload to Azure Blob Storage
        blob_handler.upload_blob(Config.AZURE_CONTAINER_NAME_PATIENT, blob_name, file_bytes)
        
        # Generate SAS URL for Document Intelligence
        sas_url = blob_handler.generate_sas_url(Config.AZURE_CONTAINER_NAME_PATIENT, blob_name)
        
        # 1. OCR
        doc_result = doc_intel.process_pdf_url(sas_url, filename)
        all_text += f"\n\n--- Document: {filename} ---\n\n" + doc_result["full_content"]
    
    # 2. PHI Masking
    scrubbed_text = phi_masker.mask_text(all_text)
    
    # 3. Entity Extraction (Async Chunked)
    entities = await patient_agent.extract(scrubbed_text)
    
    # 4. Save to Local DB
    database.save_patient(patient_id, scrubbed_text, entities)
    
    # 5. Save to Azure AI Search (Voice Bot RAG)
    patient_kb.index_document(doc_id=patient_id, text_content=scrubbed_text, entities=entities)
    print(f"[BACKGROUND] Patient {patient_id} processed successfully.")


@app.post("/upload/patient")
async def process_patient_pdf(
    background_tasks: BackgroundTasks,
    patient_id: str = Form(...),
    files: list[UploadFile] = File(...)
):
    files_data = []
    for file in files:
        file_bytes = await file.read()
        files_data.append({"bytes": file_bytes, "filename": file.filename})
    
    # Queue the heavy processing in the background so UI doesn't timeout
    background_tasks.add_task(background_process_patient, patient_id, files_data)
    
    return {"status": "processing", "message": f"Processing {len(files_data)} PDFs in background.", "patient_id": patient_id}


async def background_process_policy(policy_id: str, file_bytes: bytes, filename: str):
    print(f"[BACKGROUND] Processing Policy {policy_id}...")
    blob_name = f"{policy_id}_{filename}"
    blob_handler.upload_blob(Config.AZURE_CONTAINER_NAME_POLICY, blob_name, file_bytes)
    
    sas_url = blob_handler.generate_sas_url(Config.AZURE_CONTAINER_NAME_POLICY, blob_name)
    doc_result = doc_intel.process_pdf_url(sas_url, blob_name)
    raw_text = doc_result["full_content"]
    
    entities = await policy_agent.extract(raw_text)
    
    # Save to Local DB
    database.save_policy(policy_id, raw_text, entities)
    
    # Save to Azure AI Search
    policy_kb.index_document(policy_id, raw_text, entities)
    print(f"[BACKGROUND] Policy {policy_id} processed successfully.")


@app.post("/upload/policy")
async def upload_policy(background_tasks: BackgroundTasks, policy_id: str = Form(...), file: UploadFile = File(...)):
    file_bytes = await file.read()
    background_tasks.add_task(background_process_policy, policy_id, file_bytes, file.filename)
    
    return {"status": "processing", "message": "Policy is processing in the background.", "policy_id": policy_id}


@app.get("/api/patients")
async def get_all_patients():
    return {"status": "success", "data": database.get_all_patients()}

@app.get("/api/patients/{patient_id}")
async def get_patient_data(patient_id: str):
    data = database.get_patient(patient_id)
    if not data:
        raise HTTPException(status_code=404, detail="Patient not found in DB.")
    return {"status": "success", "data": data}

@app.get("/api/policies")
async def get_all_policies():
    return {"status": "success", "data": database.get_all_policies()}

@app.get("/api/policies/{policy_id}")
async def get_policy_data(policy_id: str):
    data = database.get_policy(policy_id)
    if not data:
        raise HTTPException(status_code=404, detail="Policy not found in DB.")
    return {"status": "success", "data": data}


@app.post("/evaluate")
async def evaluate_prior_auth(patient_id: str, policy_id: str, target_cpt: str, human_feedback: str = None):
    start_time = time.time()
    
    # Fetch from fast local DB instead of Azure Search!
    patient_doc = database.get_patient(patient_id)
    policy_doc = database.get_policy(policy_id)
    
    if not patient_doc or not policy_doc:
        raise HTTPException(status_code=404, detail="Document not found in DB. Still processing?")
        
    patient_data = json.dumps(patient_doc["entities"])
    policy_data = json.dumps(policy_doc["entities"])
    
    decision = await reasoning_agent.evaluate(patient_data, policy_data, target_cpt, human_feedback)
    
    latency = round(time.time() - start_time, 2)
    decision["processing_time_seconds"] = latency
    
    # Save decision to state DB
    request_id = f"REQ_{patient_id}_{policy_id}"
    database.create_auth_request(request_id, patient_id, policy_id, target_cpt)
    database.update_auth_request(request_id, "COMPLETED", decision)
    
    return {"decision": decision}

from pydantic import BaseModel
class ChatRequest(BaseModel):
    query: str
    patient_id: str
    policy_id: str

@app.post("/chat")
async def chat_assistant(request: ChatRequest):
    patient_doc = database.get_patient(request.patient_id)
    policy_doc = database.get_policy(request.policy_id)
    
    patient_data = json.dumps(patient_doc["entities"]) if patient_doc else "No patient data found."
    policy_data = json.dumps(policy_doc["entities"]) if policy_doc else "No policy data found."
    
    response = await chat_agent.answer_question(request.query, patient_data, policy_data)
    return {"response": response}

import base64

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    file_bytes = await file.read()
    encoded_audio = base64.b64encode(file_bytes).decode("utf-8")
    
    try:
        response = gpt_client.chat.completions.create(
            model=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "You are a professional transcriptionist. Transcribe the following audio exactly as spoken. Do not answer the question or provide commentary, just return the exact text of the speech."},
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": encoded_audio,
                                "format": "wav"
                            }
                        }
                    ]
                }
            ]
        )
        return {"text": response.choices[0].message.content}
    except Exception as e:
        print(f"[AUDIO ERROR] {e}")
        return {"text": "", "error": str(e)}

import os
from fastapi.responses import FileResponse

@app.get("/")
async def serve_spa():
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui/dist/index.html")
    response = FileResponse(index_path)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

ui_dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui/dist")
app.mount("/", StaticFiles(directory=ui_dist_path, html=False), name="ui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
