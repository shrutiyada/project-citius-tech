import sqlite3
import json
from pathlib import Path

DB_FILE = Path("prior_auth.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Patients Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            raw_text TEXT,
            entities_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Policies Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS policies (
            policy_id TEXT PRIMARY KEY,
            raw_text TEXT,
            entities_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Prior Auth Requests Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_requests (
            request_id TEXT PRIMARY KEY,
            patient_id TEXT,
            policy_id TEXT,
            target_cpt TEXT,
            status TEXT,
            decision_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY(policy_id) REFERENCES policies(policy_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_patient(patient_id: str, raw_text: str, entities: dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO patients (patient_id, raw_text, entities_json) VALUES (?, ?, ?)",
        (patient_id, raw_text, json.dumps(entities))
    )
    conn.commit()
    conn.close()

def get_patient(patient_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT raw_text, entities_json FROM patients WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"patient_id": patient_id, "raw_text": row[0], "entities": json.loads(row[1])}
    return None

def save_policy(policy_id: str, raw_text: str, entities: dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO policies (policy_id, raw_text, entities_json) VALUES (?, ?, ?)",
        (policy_id, raw_text, json.dumps(entities))
    )
    conn.commit()
    conn.close()

def get_policy(policy_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT raw_text, entities_json FROM policies WHERE policy_id = ?", (policy_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"policy_id": policy_id, "raw_text": row[0], "entities": json.loads(row[1])}
    return None

def create_auth_request(request_id: str, patient_id: str, policy_id: str, target_cpt: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO auth_requests (request_id, patient_id, policy_id, target_cpt, status) VALUES (?, ?, ?, ?, 'PROCESSING')",
        (request_id, patient_id, policy_id, target_cpt)
    )
    conn.commit()
    conn.close()

def update_auth_request(request_id: str, status: str, decision: dict = None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if decision:
        cursor.execute(
            "UPDATE auth_requests SET status = ?, decision_json = ?, updated_at = CURRENT_TIMESTAMP WHERE request_id = ?",
            (status, json.dumps(decision), request_id)
        )
    else:
        cursor.execute(
            "UPDATE auth_requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE request_id = ?",
            (status, request_id)
        )
    conn.commit()
    conn.close()

def get_auth_request(request_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT status, decision_json FROM auth_requests WHERE request_id = ?", (request_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"request_id": request_id, "status": row[0], "decision": json.loads(row[1]) if row[1] else None}
    return None
