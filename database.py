import json
from datetime import datetime
import uuid
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from config import Config

# Initialize Cosmos DB Client lazily or globally
_client = None
_db = None
_patients_container = None
_policies_container = None
_auth_container = None

def _get_containers():
    global _client, _db, _patients_container, _policies_container, _auth_container
    if _client is None:
        try:
            _client = CosmosClient(Config.AZURE_COSMOS_ENDPOINT, credential=Config.AZURE_COSMOS_KEY)
            _db = _client.get_database_client("PriorAuthDB")
            _patients_container = _db.get_container_client("Patients")
            _policies_container = _db.get_container_client("Policies")
            _auth_container = _db.get_container_client("AuthRequests")
        except Exception as e:
            print(f"[COSMOS ERROR] Failed to connect or get containers: {e}")
            raise
    return _patients_container, _policies_container, _auth_container

def init_db():
    if not Config.AZURE_COSMOS_ENDPOINT or not Config.AZURE_COSMOS_KEY:
        print("[COSMOS WARNING] AZURE_COSMOS_ENDPOINT or AZURE_COSMOS_KEY not set. Cannot initialize Cosmos DB.")
        return

    try:
        client = CosmosClient(Config.AZURE_COSMOS_ENDPOINT, credential=Config.AZURE_COSMOS_KEY)
        # Create DB if it doesn't exist
        db = client.create_database_if_not_exists(id="PriorAuthDB")
        
        # Create Containers if they don't exist
        db.create_container_if_not_exists(
            id="Patients",
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400
        )
        db.create_container_if_not_exists(
            id="Policies",
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400
        )
        db.create_container_if_not_exists(
            id="AuthRequests",
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400
        )
        print("[COSMOS DB] Successfully initialized database and containers.")
    except Exception as e:
        print(f"[COSMOS ERROR] Initialization failed: {e}")

def save_patient(patient_id: str, raw_text: str, entities: dict):
    patients_c, _, _ = _get_containers()
    doc = {
        "id": patient_id,
        "raw_text": raw_text,
        "entities": entities,
        "created_at": datetime.utcnow().isoformat()
    }
    patients_c.upsert_item(doc)

def get_patient(patient_id: str):
    patients_c, _, _ = _get_containers()
    try:
        doc = patients_c.read_item(item=patient_id, partition_key=patient_id)
        return {"patient_id": doc["id"], "raw_text": doc["raw_text"], "entities": doc["entities"]}
    except exceptions.CosmosResourceNotFoundError:
        return None

def get_all_patients():
    patients_c, _, _ = _get_containers()
    query = "SELECT c.id FROM c ORDER BY c.created_at DESC"
    results = list(patients_c.query_items(query=query, enable_cross_partition_query=True))
    return [r["id"] for r in results]

def save_policy(policy_id: str, raw_text: str, entities: dict):
    _, policies_c, _ = _get_containers()
    doc = {
        "id": policy_id,
        "raw_text": raw_text,
        "entities": entities,
        "created_at": datetime.utcnow().isoformat()
    }
    policies_c.upsert_item(doc)

def get_policy(policy_id: str):
    _, policies_c, _ = _get_containers()
    try:
        doc = policies_c.read_item(item=policy_id, partition_key=policy_id)
        return {"policy_id": doc["id"], "raw_text": doc["raw_text"], "entities": doc["entities"]}
    except exceptions.CosmosResourceNotFoundError:
        return None

def get_all_policies():
    _, policies_c, _ = _get_containers()
    query = "SELECT c.id FROM c ORDER BY c.created_at DESC"
    results = list(policies_c.query_items(query=query, enable_cross_partition_query=True))
    return [r["id"] for r in results]

def create_auth_request(request_id: str, patient_id: str, policy_id: str, target_cpt: str):
    _, _, auth_c = _get_containers()
    doc = {
        "id": request_id,
        "patient_id": patient_id,
        "policy_id": policy_id,
        "target_cpt": target_cpt,
        "status": "PROCESSING",
        "pa_state": "PENDED", # Default PA state before evaluation
        "decision": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    auth_c.upsert_item(doc)

def update_auth_request(request_id: str, status: str, decision: dict = None):
    _, _, auth_c = _get_containers()
    try:
        doc = auth_c.read_item(item=request_id, partition_key=request_id)
        doc["status"] = status
        doc["updated_at"] = datetime.utcnow().isoformat()
        if decision:
            doc["decision"] = decision
            
            # Extract final AI decision string to determine the patient's PA state
            decision_text = decision.get("decision", "").upper()
            if "APPROVE" in decision_text:
                doc["pa_state"] = "APPROVED"
            elif "DENY" in decision_text or "DENIED" in decision_text:
                doc["pa_state"] = "DENIED"
            else:
                doc["pa_state"] = "PENDED"
                
        auth_c.replace_item(item=request_id, body=doc)
    except exceptions.CosmosResourceNotFoundError:
        print(f"[COSMOS ERROR] Auth Request {request_id} not found.")

def get_auth_request(request_id: str):
    _, _, auth_c = _get_containers()
    try:
        doc = auth_c.read_item(item=request_id, partition_key=request_id)
        return {
            "request_id": doc["id"], 
            "status": doc["status"], 
            "pa_state": doc.get("pa_state", "UNKNOWN"),
            "decision": doc.get("decision")
        }
    except exceptions.CosmosResourceNotFoundError:
        return None
