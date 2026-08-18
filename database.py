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
            pa_state TEXT DEFAULT 'PENDED',
            decision_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY(policy_id) REFERENCES policies(policy_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[SQLITE DB] Successfully initialized database and tables.")

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

def get_all_patients():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

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

def get_all_policies():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT policy_id FROM policies ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def create_auth_request(request_id: str, patient_id: str, policy_id: str, target_cpt: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO auth_requests (request_id, patient_id, policy_id, target_cpt, status, pa_state) VALUES (?, ?, ?, ?, 'PROCESSING', 'PENDED')",
        (request_id, patient_id, policy_id, target_cpt)
    )
    conn.commit()
    conn.close()

def update_auth_request(request_id: str, status: str, decision: dict = None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if decision:
        pa_state = "PENDED"
        decision_text = decision.get("decision", "").upper()
        if "APPROVE" in decision_text:
            pa_state = "APPROVED"
        elif "DENY" in decision_text or "DENIED" in decision_text:
            pa_state = "DENIED"
            
        cursor.execute(
            "UPDATE auth_requests SET status = ?, pa_state = ?, decision_json = ?, updated_at = CURRENT_TIMESTAMP WHERE request_id = ?",
            (status, pa_state, json.dumps(decision), request_id)
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
    cursor.execute("SELECT status, pa_state, decision_json FROM auth_requests WHERE request_id = ?", (request_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "request_id": request_id, 
            "status": row[0], 
            "pa_state": row[1],
            "decision": json.loads(row[2]) if row[2] else None
        }
    return None
