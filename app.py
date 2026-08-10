import streamlit as st
import requests

st.set_page_config(page_title="Prior Auth Decision Engine", layout="wide")
API_URL = "http://localhost:8000"

# Initialize Session State
if "patient_id" not in st.session_state:
    st.session_state.patient_id = ""
if "policy_id" not in st.session_state:
    st.session_state.policy_id = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "eval_result" not in st.session_state:
    st.session_state.eval_result = None

st.title("🏥 Prior Auth")

tab1, tab2 = st.tabs(["Prior Auth Pipeline", "Medical Assistant Chat"])

with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.header("1. Upload Patient Record(s)")
        p_id_input = st.text_input("Patient Profile ID", placeholder="e.g. PATIENT-123", key="upload_p_id")
        patient_files = st.file_uploader("Upload Patient PDF(s)", type=["pdf"], accept_multiple_files=True)
        
        if st.button("Process Patient Record(s)") and patient_files and p_id_input:
            with st.spinner(f"Uploading & Processing {len(patient_files)} files via Azure..."):
                files_payload = [("files", (f.name, f.getvalue(), "application/pdf")) for f in patient_files]
                data = {"patient_id": p_id_input}
                
                res = requests.post(f"{API_URL}/upload/patient", files=files_payload, data=data)
                if res.status_code == 200:
                    st.success(f"Successfully processed {len(patient_files)} documents for {p_id_input}")
                    st.session_state.patient_id = p_id_input
                    st.json(res.json().get("entities", {}))
                else:
                    st.error("Error processing patient files.")

    with col2:
        st.header("2. Upload Medical Policy")
        pol_id_input = st.text_input("Policy ID", placeholder="e.g. POLICY-AETNA-99213", key="upload_pol_id")
        policy_file = st.file_uploader("Upload Policy PDF", type=["pdf"])
        
        if st.button("Process Medical Policy") and policy_file and pol_id_input:
            with st.spinner("Extracting Policy Criteria..."):
                files = {"file": (policy_file.name, policy_file.getvalue(), "application/pdf")}
                data = {"policy_id": pol_id_input}
                
                res = requests.post(f"{API_URL}/upload/policy", files=files, data=data)
                if res.status_code == 200:
                    st.success(f"Successfully indexed Policy {pol_id_input}")
                    st.session_state.policy_id = pol_id_input
                    st.json(res.json().get("entities", {}))
                else:
                    st.error("Error processing policy file.")

    st.divider()

    st.header("3. Run Prior Auth Review (with Critique)")
    c1, c2, c3 = st.columns(3)
    with c1:
        p_id_eval = st.text_input("Patient Document ID", value=st.session_state.patient_id, key="p_id_eval")
    with c2:
        pol_id_eval = st.text_input("Policy Document ID", value=st.session_state.policy_id, key="pol_id_eval")
    with c3:
        cpt = st.text_input("Requested CPT Code", placeholder="e.g. 99213", key="cpt_code_input")

    def run_evaluation(human_feedback=None):
        if p_id_eval and pol_id_eval:
            with st.spinner("AI Reviewing Medical Necessity Criteria and Auditing Decision..."):
                params = {
                    "patient_id": p_id_eval, 
                    "policy_id": pol_id_eval, 
                    "target_cpt": st.session_state.cpt_code_input if st.session_state.cpt_code_input else ""
                }
                if human_feedback:
                    params["human_feedback"] = human_feedback
                    
                res = requests.post(f"{API_URL}/evaluate", params=params)
                
                if res.status_code == 200:
                    st.session_state.eval_result = res.json()["decision"]
                else:
                    st.error(f"Error: {res.text}")
        else:
            st.warning("Please fill in all fields.")

    if st.button("Evaluate Prior Auth Decision", type="primary"):
        run_evaluation()
        
    if st.session_state.eval_result:
        data = st.session_state.eval_result
        decision = data.get("decision", "UNKNOWN")
        
        st.markdown("---")
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
        elif audit_status == "MANUAL_OVERRIDE":
            st.info("👤 **Manual Override**: The decision was manually forced by a human auditor.")
        else:
            st.error(f"❌ **Audit Failed**: {data.get('audit_feedback', 'No feedback provided.')}")
            
        st.markdown("### Matched Policy Criteria:")
        st.write(data.get("matched_criteria", "None"))
        
        st.divider()
        st.subheader("👤 Human Auditor Override (HITL)")
        st.markdown("If the policy criteria changed, or the AI made a mistake, you can manually override the decision here.")
        
        hitl_feedback = st.text_area("Human Override Instructions (e.g. 'Approve this, bypass step-therapy because policy changed yesterday')")
        hitl_audio = st.audio_input("Or speak your override instructions...", key="hitl_audio")
        
        if st.button("Submit Human Override"):
            final_hitl = hitl_feedback
            if hitl_audio and not final_hitl:
                with st.spinner("Transcribing Override Voice..."):
                    files = {"file": (hitl_audio.name, hitl_audio.getvalue(), "audio/wav")}
                    res_audio = requests.post(f"{API_URL}/transcribe", files=files)
                    if res_audio.status_code == 200:
                        res_data = res_audio.json()
                        if res_data.get("error"):
                            st.error(f"Transcription Error: {res_data.get('error')}")
                        else:
                            final_hitl = res_data.get("text", "")
                            
            if final_hitl:
                run_evaluation(human_feedback=final_hitl)
                st.rerun()
            else:
                st.warning("Please provide feedback (text or voice) to override.")

with tab2:
    st.header("💬 AI Medical Assistant Chat")
    st.markdown("Ask questions about the uploaded patient data and medical policies.")
    
    chat_p_id = st.session_state.patient_id
    chat_pol_id = st.session_state.policy_id
        
    st.divider()
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Input mechanisms
    prompt = st.chat_input("Ask a question about the policy or patient...")
    audio_val = st.audio_input("Or speak your question...")
    
    final_query = None
    if prompt:
        final_query = prompt
    elif audio_val:
        with st.spinner("Transcribing Voice..."):
            files = {"file": (audio_val.name, audio_val.getvalue(), "audio/wav")}
            res_audio = requests.post(f"{API_URL}/transcribe", files=files)
            if res_audio.status_code == 200:
                res_data = res_audio.json()
                if res_data.get("error"):
                    st.error(f"Transcription Error: {res_data.get('error')}")
                else:
                    final_query = res_data.get("text", "")
            else:
                st.error("Failed to transcribe audio.")
                
    if final_query:
        if not chat_p_id or not chat_pol_id:
            st.error("Please ensure Patient ID and Policy ID are filled in above.")
        else:
            st.session_state.messages.append({"role": "user", "content": final_query})
            with st.chat_message("user"):
                st.markdown(final_query)
                
            with st.chat_message("assistant"):
                with st.spinner("Searching Knowledge Base..."):
                    payload = {
                        "query": final_query,
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
