from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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
from openai import AzureOpenAI

app = FastAPI(title="Prior Auth Decision Engine API")

# Initialize shared resources
if not Config.validate_all():
    raise RuntimeError("Missing configuration.")

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


@app.post("/upload/patient")
async def process_patient_pdf(
    patient_id: str = Form(...),
    files: list[UploadFile] = File(...)
):
    start_time = time.time()
    all_text = ""
    for file in files:
        temp_pdf = f"temp_{file.filename}"
        with open(temp_pdf, "wb") as f:
            f.write(await file.read())
        
        # 1. OCR (with Page Numbers and Bounding Boxes)
        doc_result = doc_intel.process_pdf_url(temp_pdf, file.filename)
        all_text += doc_result["full_content"] + "\n\n"
        
    # 2. PHI Masking
    scrubbed_text = phi_masker.mask_phi(all_text)
    
    # 3. Entity Extraction (Diagnoses, Procedures, Citations)
    entities = await patient_agent.extract(scrubbed_text)
    
    # 4. Save to Azure AI Search
    kb_indexer.index_document(doc_id=patient_id, text_content=scrubbed_text, entities=entities)
    
    latency = round(time.time() - start_time, 2)
    return {"status": "success", "patient_id": patient_id, "entities": entities, "processing_time_seconds": latency}

@app.post("/upload/policy")
async def upload_policy(policy_id: str = Form(...), file: UploadFile = File(...)):
    start_time = time.time()
    file_bytes = await file.read()
    blob_name = f"{policy_id}_{file.filename}"
    blob_handler.upload_blob(Config.AZURE_CONTAINER_NAME_POLICY, blob_name, file_bytes)
    
    sas_url = blob_handler.generate_sas_url(Config.AZURE_CONTAINER_NAME_POLICY, blob_name)
    raw_text = doc_intel.process_pdf_url(sas_url, blob_name)["full_content"]
    
    entities = await policy_agent.extract(raw_text)
    policy_kb.index_document(policy_id, raw_text, entities)
    
    latency = round(time.time() - start_time, 2)
    return {"status": "success", "policy_id": policy_id, "entities": entities, "processing_time_seconds": latency}

@app.post("/evaluate")
async def evaluate_prior_auth(patient_id: str, policy_id: str, target_cpt: str, human_feedback: str = None):
    start_time = time.time()
    patient_doc = patient_kb.get_document(patient_id)
    policy_doc = policy_kb.get_document(policy_id)
    
    if not patient_doc or not policy_doc:
        raise HTTPException(status_code=404, detail="Document not found in KB.")
        
    patient_data = patient_doc.get("entities_metadata", "")
    policy_data = policy_doc.get("entities_metadata", "")
    
    if not isinstance(patient_data, str) or not patient_data.startswith("{"):
        patient_data = json.dumps(patient_data)
        
    if not isinstance(policy_data, str) or not policy_data.startswith("{"):
        policy_data = json.dumps(policy_data)
    
    decision = await reasoning_agent.evaluate(patient_data, policy_data, target_cpt, human_feedback)
    
    latency = round(time.time() - start_time, 2)
    decision["processing_time_seconds"] = latency
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

# Serve React Frontend Statically
ui_dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui/dist")
app.mount("/", StaticFiles(directory=ui_dist_path, html=True), name="ui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
