import streamlit as st
import requests
import json

st.set_page_config(page_title="Prior Auth Decision Engine", layout="wide")
API_URL = "http://localhost:8000"

st.title("🏥 Automated Prior Auth Decision Engine")

col1, col2 = st.columns(2)

with col1:
    st.header("1. Upload Patient Record")
    patient_file = st.file_uploader("Upload Patient PDF", type=["pdf"])
    if st.button("Process Patient Record") and patient_file:
        with st.spinner("Uploading & Processing via Azure..."):
            files = {"file": (patient_file.name, patient_file.getvalue(), "application/pdf")}
            res = requests.post(f"{API_URL}/upload/patient", files=files)
            if res.status_code == 200:
                st.success(f"Indexed as: {patient_file.name}")
                st.json(res.json()["entities"])
            else:
                st.error("Error processing patient file.")

with col2:
    st.header("2. Upload Medical Policy")
    policy_file = st.file_uploader("Upload Policy PDF", type=["pdf"])
    if st.button("Process Medical Policy") and policy_file:
        with st.spinner("Extracting Policy Criteria..."):
            files = {"file": (policy_file.name, policy_file.getvalue(), "application/pdf")}
            res = requests.post(f"{API_URL}/upload/policy", files=files)
            if res.status_code == 200:
                st.success(f"Indexed as: {policy_file.name}")
                st.json(res.json()["entities"])
            else:
                st.error("Error processing policy file.")

st.divider()

st.header("3. Run Prior Auth Review")
c1, c2, c3 = st.columns(3)
with c1:
    p_id = st.text_input("Patient Document ID", placeholder="e.g. patient_record.pdf")
with c2:
    pol_id = st.text_input("Policy Document ID", placeholder="e.g. policy.pdf")
with c3:
    cpt = st.text_input("Requested CPT Code", placeholder="e.g. 99213")

if st.button("Evaluate Prior Auth Decision", type="primary"):
    if p_id and pol_id and cpt:
        with st.spinner("AI Reviewing Medical Necessity Criteria..."):
            params = {"patient_id": p_id, "policy_id": pol_id, "target_cpt": cpt}
            res = requests.post(f"{API_URL}/evaluate", params=params)
            
            if res.status_code == 200:
                data = res.json()["decision"]
                decision = data.get("decision", "UNKNOWN")
                
                if decision == "APPROVE":
                    st.success("✅ **APPROVED**")
                elif decision == "DENY":
                    st.error("❌ **DENIED**")
                else:
                    st.warning("⚠️ **PENDING REVIEW**")
                    
                st.markdown("### Reasoning:")
                st.write(data.get("reasoning", ""))
                st.markdown("### Matched Policy Criteria:")
                st.info(data.get("matched_criteria", ""))
            else:
                st.error(f"Error: {res.text}")
    else:
        st.warning("Please fill in all fields.")
