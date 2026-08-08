# Automated Prior Auth Decision Engine

This is a production-grade, decoupled AI system built with a **FastAPI backend** and a **Streamlit frontend**, powered by the **Microsoft Agent Framework (Semantic Kernel)** and **Azure OpenAI**.

## Architecture & Agents
The system features a multi-agent orchestration architecture:
1. **Patient Pipeline (`patient_agent.py`)**: Extracts patient diagnoses and requested procedures, masking all PHI using Microsoft Presidio. Stores in `patient-auth-index`.
2. **Policy Pipeline (`policy_agent.py`)**: Extracts medical criteria, exclusions, and covered CPT codes. Stores in `medical-policy-index`.
3. **Reasoning & Critique Loop (`reasoning_agent.py`)**: A dual-agent setup. The Reasoning Agent evaluates the patient history against the medical policy. The Critique Agent (Auditor) reviews the logic and can reject it, forcing a self-reflection loop before generating the final APPROVE/DENY/PEND decision.
4. **Medical Assistant Chat (`chat_agent.py`)**: A RAG-powered chatbot that lets you query both the patient data and policy rules simultaneously.

## Setup

1. Copy `env_example.txt` to `.env` and fill in your keys (You must use Azure OpenAI Foundry keys).
2. Ensure you have activated your virtual environment:
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
*(You can view the interactive API docs at `http://localhost:8000/docs`)*

**Terminal 2: Start the Streamlit Frontend**
```bash
source venv/bin/activate
streamlit run app.py
```
This will automatically open your web browser to the interactive UI dashboard!
