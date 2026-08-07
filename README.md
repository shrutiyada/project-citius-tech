# Automated Prior Auth Decision Engine

This is a decoupled AI system with a **FastAPI backend** and a **Streamlit frontend**.

## Architecture
1. **Patient Pipeline**: Extracts patient diagnoses and requested procedures, masking all PHI. Stores in `patient-auth-index`.
2. **Policy Pipeline**: Extracts medical criteria, exclusions, and covered CPT codes. Stores in `medical-policy-index`.
3. **Reasoning Agent**: Evaluates the patient history against the medical policy for a specific CPT code to generate an APPROVE/DENY/PEND decision.

## Setup

1. Copy `.env.example` to `.env` and fill in your keys.
2. Activate your environment:
```bash
source venv/bin/activate
```

## How to Run

You need two terminal windows open to run the decoupled architecture.

**Terminal 1: Start the FastAPI Backend**
```bash
source venv/bin/activate
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```
(You can view the interactive API docs at `http://localhost:8000/docs`)

**Terminal 2: Start the Streamlit Frontend**
```bash
source venv/bin/activate
streamlit run app.py
```
This will automatically open your web browser to the UI!
