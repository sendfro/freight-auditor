import streamlit as st
import tempfile
import os
import time
import csv
import pandas as pd
from io import BytesIO

# Import the core engine tools
from extractor import extract_invoice_data
from auditor import run_audit
from disputer import generate_dispute_email
from mailer import fire_dispute_email

# 1. Initialize Memory & Configuration
st.set_page_config(page_title="Sendfro | AI Freight Auditor", layout="centered")

if "history" not in st.session_state:
    st.session_state["history"] = []
if "pipeline_run" not in st.session_state:
    st.session_state["pipeline_run"] = False

st.title("🚛 Sendfro: Automated Freight Auditor")
st.write("Extract data, audit against target costs, and dispatch dispute emails instantly.")

st.markdown("---")

# 2. Step 1: Expected Costs
st.subheader("Step 1: Define Expected Costs")
cost_mode = st.radio(
    "How do you want to establish the Expected Target Cost?",
    ["✏️ Manual Entry (Quick Audit)", "📊 Upload Expected Costs CSV (Batch Audit)"]
)

expected_total_manual = 0.0
csv_data_dict = {}

if cost_mode == "✏️ Manual Entry (Quick Audit)":
    expected_total_manual = st.number_input("What is the Expected Invoice Total? ($)", value=1100.00, step=10.00)
else:
    st.info("Your CSV must have 'invoice_number' and 'expected_cost'")
    csv_file = st.file_uploader("Upload Expected Costs Database (CSV)", type=["csv"])
    if csv_file is not None:
        decoded_file = csv_file.getvalue().decode('utf-8').splitlines()
        reader = csv.reader(decoded_file)
        next(reader, None) 
        for row in reader:
            if len(row) >= 2:
                inv_num = str(row[0]).strip()
                try:
                    csv_data_dict[inv_num] = float(row[1].strip())
                except ValueError: pass
        st.success(f"✅ Loaded {len(csv_data_dict)} costs!")

st.markdown("---")

# 3. Step 2: Invoice Upload
st.subheader("Step 2: Upload Carrier Invoices")
uploaded_files = st.file_uploader("Drop invoice images (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Run Freight Pipeline", type="primary"):
        st.session_state["pipeline_run"] = True
        
    if st.session_state["pipeline_run"]:
        for uploaded_file in uploaded_files:
            st.markdown(f"## 📄 Processing: {uploaded_file.name}")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_image_path = temp_file.name

            try:
                with st.spinner(f"AI Extraction in progress..."):
                    extracted_data = extract_invoice_data(temp_image_path)
                    st.json(extracted_data) 

                extracted_inv_num = str(extracted_data.get("invoice_number", "UNKNOWN"))
                target_cost = csv_data_dict.get(extracted_inv_num, expected_total_manual) if cost_mode == "📊 Upload Expected Costs CSV (Batch Audit)" else expected_total_manual

                with st.spinner("Running Reconciliation Audit..."):
                    simulated_db = {extracted_inv_num: {"expected_total": target_cost, "approved_fees": []}}
                    audit_report = run_audit(extracted_data, simulated_db)
                
                st.markdown("### 📊 Audit Results")
                
                if audit_report["status"] == "DISPUTE REQUIRED":
                    st.error(f"Status: DISPUTE REQUIRED (Variance: ${audit_report['total_disputed_amount']})")
                    for flag in audit_report["flags"]:
                        st.warning(flag)
                    
                    st.markdown("### ✉️ Auto-Drafted Dispute Email")
                    email_draft = generate_dispute_email(audit_report, {"carrier_name": extracted_data.get("carrier_name", "Carrier"), "invoice_number": extracted_inv_num})
                    final_email_text = st.text_area(f"Edit draft:", value=email_draft, height=200, key=f"draft_{uploaded_file.name}")
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        rep_email = st.text_input("Carrier Rep Email:", placeholder="rep@dhl.com", key=f"email_{uploaded_file.name}")
                    with col2:
                        st.write("") # Spacing
                        st.write("") # Spacing
                        if st.button("📨 Send Dispute Now", key=f"send_{uploaded_file.name}", type="primary"):
                            if rep_email:
                                with st.spinner("Sending..."):
                                    success, msg = fire_dispute_email(rep_email, f"Dispute: Inv {extracted_inv_num}", final_email_text)
                                    if success:
                                        st.success("✅ Sent!")
                                        # SAVE TO HISTORY
                                        st.session_state["history"].append({
                                            "Timestamp": time.strftime("%Y-%m-%d %H:%M"),
                                            "Invoice": extracted_inv_num,
                                            "Carrier": extracted_data.get("carrier_name", "Carrier"),
                                            "Disputed_Amount": float(audit_report['total_disputed_amount']),
                                            "Status": "SENT"
                                        })
                                    else: st.error(msg)
                            else: st.warning("Enter email.")
                else: 
                    st.success("✅ Invoice Approved: Matches target cost.")

            except Exception as e: st.error(f"Error: {e}")
            finally:
                if os.path.exists(temp_image_path): os.remove(temp_image_path)
            st.markdown("---")

# 4. Step 3: Pro History Dashboard
st.subheader("📋 Audit & Dispute History")
if st.session_state["history"]:
    # Convert history to DataFrame for clean display and export
    df_history = pd.DataFrame(st.session_state["history"])
    st.dataframe(df_history, use_container_width=True)
    
    total_saved = df_history["Disputed_Amount"].sum()
    
    col_metric, col_download = st.columns([2, 1])
    with col_metric:
        st.metric("Total Potential Recovery", f"${total_saved:,.2f}")
    
    with col_download:
        # Generate CSV for download
        csv_buffer = BytesIO()
        df_history.to_csv(csv_buffer, index=False)
        st.write("") # Spacing
        st.download_button(
            label="📥 Download Audit Log",
            data=csv_buffer.getvalue(),
            file_name=f"sendfro_audit_log_{time.strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
else:
    st.info("No disputes sent yet in this session.")