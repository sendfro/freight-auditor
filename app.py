import streamlit as st
import tempfile
import os
import time
import csv 

# Import the core engine tools
from extractor import extract_invoice_data
from auditor import run_audit
from disputer import generate_dispute_email
from mailer import fire_dispute_email

st.set_page_config(page_title="AI Freight Auditor", layout="centered")

st.title("🚛 Automated Freight Auditor")
st.write("Upload carrier invoices to extract data, audit against your expected costs, and automatically draft dispute emails if you are overcharged.")

st.markdown("---")

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
    st.info("Your CSV must have two columns: 'invoice_number' and 'expected_cost'")
    csv_file = st.file_uploader("Upload your Expected Costs Database (CSV)", type=["csv"])
    
    if csv_file is not None:
        decoded_file = csv_file.getvalue().decode('utf-8').splitlines()
        reader = csv.reader(decoded_file)
        next(reader, None) 
        for row in reader:
            if len(row) >= 2:
                inv_num = str(row[0]).strip()
                try:
                    cost = float(row[1].strip())
                    csv_data_dict[inv_num] = cost
                except ValueError:
                    pass
        st.success(f"✅ Successfully loaded {len(csv_data_dict)} expected costs into memory!")

st.markdown("---")

st.subheader("Step 2: Upload Carrier Invoices")
uploaded_files = st.file_uploader("Drop your invoice images here (JPG or PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

# THE FIX: Give the app a memory so it doesn't close the door on you!
if "pipeline_run" not in st.session_state:
    st.session_state["pipeline_run"] = False

if uploaded_files:
    if st.button("🚀 Run Freight Pipeline", type="primary"):
        st.session_state["pipeline_run"] = True
        
    if st.session_state["pipeline_run"]:
        for uploaded_file in uploaded_files:
            st.markdown(f"## 📄 Processing: {uploaded_file.name}")
            st.image(uploaded_file, caption=f"Uploaded: {uploaded_file.name}")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_image_path = temp_file.name

            try:
                with st.spinner(f"Extracting data from {uploaded_file.name}..."):
                    extracted_data = extract_invoice_data(temp_image_path)
                    st.json(extracted_data) 
                    time.sleep(1)

                extracted_inv_num = str(extracted_data.get("invoice_number", "UNKNOWN"))
                
                if cost_mode == "📊 Upload Expected Costs CSV (Batch Audit)":
                    if extracted_inv_num in csv_data_dict:
                        target_cost = csv_data_dict[extracted_inv_num]
                        st.info(f"🔍 Found Invoice '{extracted_inv_num}' in CSV. Target Cost: ${target_cost}")
                    else:
                        st.warning(f"⚠️ Invoice '{extracted_inv_num}' not found in your CSV. Flagging for manual review.")
                        target_cost = 0.0
                else:
                    target_cost = expected_total_manual

                with st.spinner("Running Reconciliation Audit..."):
                    simulated_db = {
                        extracted_inv_num: {
                            "expected_total": target_cost,
                            "approved_fees": []
                        }
                    }
                    audit_report = run_audit(extracted_data, simulated_db)
                
                st.markdown("### 📊 Audit Results")
                
                if audit_report["status"] == "DISPUTE REQUIRED":
                    st.error(f"Status: {audit_report['status']} (Variance: ${audit_report['total_disputed_amount']})")
                    for flag in audit_report["flags"]:
                        st.warning(flag)
                    
                    st.markdown("### ✉️ Auto-Drafted Dispute Email")
                    
                    with st.spinner("Drafting carrier communication..."):
                        invoice_details = {
                            "carrier_name": extracted_data.get("carrier_name", "Carrier"),
                            "invoice_number": extracted_inv_num
                        }
                        email_draft = generate_dispute_email(audit_report, invoice_details)
                        
                        final_email_text = st.text_area(f"Review draft for {uploaded_file.name}:", value=email_draft, height=250, key=f"draft_{uploaded_file.name}")
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            carrier_rep_email = st.text_input("Carrier Rep Email Address:", placeholder="rep@dhl.com", key=f"email_{uploaded_file.name}")
                        with col2:
                            st.write("") 
                            st.write("") 
                            if st.button("📨 Send Dispute Now", key=f"send_{uploaded_file.name}", type="primary"):
                                if carrier_rep_email:
                                    with st.spinner("Transmitting to carrier..."):
                                        success, msg = fire_dispute_email(
                                            carrier_email=carrier_rep_email,
                                            subject=f"URGENT: Billing Dispute - Invoice {extracted_inv_num}",
                                            body=final_email_text
                                        )
                                        if success:
                                            st.success(msg)
                                        else:
                                            st.error(msg)
                                else:
                                    st.warning("⚠️ Please enter a carrier email address first.")
                else: 
                    st.success(f"Status: {audit_report['status']}")
                    st.info("Invoice matches target cost. Approved for payment.")

            except Exception as e:
                st.error(f"Pipeline Failed for {uploaded_file.name}: {e}")
                
            finally:
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
            
            st.markdown("---")