import streamlit as st
import requests

st.set_page_config(page_title="Prior Auth Decision Engine", layout="wide")
API_URL = "http://localhost:8000"

st.title("🏥 Automated Prior Auth Decision Engine")

tab1, tab2 = st.tabs(["Prior Auth Pipeline", "Medical Assistant Chat"])

with tab1:
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
                    st.json(res.json().get("entities", {}))
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
                    st.json(res.json().get("entities", {}))
                else:
                    st.error("Error processing policy file.")

    st.divider()

    st.header("3. Run Prior Auth Review (with Critique)")
    c1, c2, c3 = st.columns(3)
    with c1:
        p_id = st.text_input("Patient Document ID", placeholder="e.g. patient_record.pdf", key="p_id_eval")
    with c2:
        pol_id = st.text_input("Policy Document ID", placeholder="e.g. policy.pdf", key="pol_id_eval")
    with c3:
        cpt = st.text_input("Requested CPT Code", placeholder="e.g. 99213")

    if st.button("Evaluate Prior Auth Decision", type="primary"):
        if p_id and pol_id and cpt:
            with st.spinner("AI Reviewing Medical Necessity Criteria and Auditing Decision..."):
                params = {"patient_id": p_id, "policy_id": pol_id, "target_cpt": cpt}
                res = requests.post(f"{API_URL}/evaluate", params=params)
                
                if res.status_code == 200:
                    data = res.json()["decision"]
                    decision = data.get("decision", "UNKNOWN")
                    
                    if decision == "APPROVE":
                        st.success("✅ **FINAL DECISION: APPROVED**")
                    elif decision == "DENY":
                        st.error("❌ **FINAL DECISION: DENIED**")
                    else:
                        st.warning("⚠️ **FINAL DECISION: PENDING REVIEW**")
                        
                    st.markdown("### Initial Reasoning:")
                    st.write(data.get("reasoning", "No reasoning provided."))
                    
                    st.markdown("### Critique Audit Status:")
                    audit_status = data.get("audit_status", "UNKNOWN")
                    if audit_status == "PASS":
                        st.info("✅ **Audit Passed**: The reasoning logic is sound and matches policy criteria.")
                    else:
                        st.error(f"❌ **Audit Failed**: {data.get('audit_feedback', 'No feedback provided.')}")
                        
                    st.markdown("### Matched Policy Criteria:")
                    st.write(data.get("matched_criteria", "None"))
                else:
                    st.error(f"Error: {res.text}")
        else:
            st.warning("Please fill in all fields.")

with tab2:
    st.header("💬 AI Medical Assistant Chat")
    st.markdown("Ask questions about the uploaded patient data and medical policies.")
    
    colA, colB = st.columns(2)
    with colA:
        chat_p_id = st.text_input("Patient Document ID", placeholder="patient_record.pdf", key="p_id_chat")
    with colB:
        chat_pol_id = st.text_input("Policy Document ID", placeholder="policy.pdf", key="pol_id_chat")
        
    st.divider()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Ask a question about the policy or patient..."):
        if not chat_p_id or not chat_pol_id:
            st.error("Please enter both a Patient ID and Policy ID above to chat with the data.")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("Searching Knowledge Base..."):
                    payload = {
                        "query": prompt,
                        "patient_id": chat_p_id,
                        "policy_id": chat_pol_id
                    }
                    res = requests.post(f"{API_URL}/chat", json=payload)
                    
                    if res.status_code == 200:
                        response_text = res.json().get("response", "")
                        st.markdown(response_text)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    else:
                        st.error(f"Error communicating with Chat API: {res.text}")
