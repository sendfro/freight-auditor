import streamlit as st
import tempfile
import os
import time

# Import the core engine you already built!
from extractor import extract_invoice_data
from auditor import run_audit
from disputer import generate_dispute_email

# Configure the look of the website
st.set_page_config(page_title="AI Freight Auditor", layout="centered")

st.title("🚛 Automated Freight Auditor")
st.write("Upload carrier invoices to extract data, audit against your expected costs, and automatically draft dispute emails if you are overcharged.")

st.markdown("---")

# Let the user type in what they expected to pay
expected_total = st.number_input("What is the Expected Invoice Total for these shipments? ($)", value=1100.00, step=10.00)

# THE UPGRADE: accept_multiple_files=True allows batch uploading!
uploaded_files = st.file_uploader("Drop your invoice images here (JPG or PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

# If the user uploaded at least one file, show the button
if uploaded_files:
    if st.button("🚀 Run Freight Pipeline", type="primary"):
        
        # THE LOOP: The engine will now run for every single file in the batch
        for uploaded_file in uploaded_files:
            
            st.markdown(f"## 📄 Processing: {uploaded_file.name}")
            st.image(uploaded_file, caption=f"Uploaded: {uploaded_file.name}", use_container_width=True)
            
            # Save the uploaded file temporarily so your extractor can read it
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_image_path = temp_file.name

            try:
                # --- PHASE 1: THE EYES ---
                with st.spinner(f"Extracting data from {uploaded_file.name}..."):
                    extracted_data = extract_invoice_data(temp_image_path)
                    st.success("Data Extraction Complete!")
                    st.json(extracted_data) 
                    time.sleep(1)

                # --- PHASE 2: THE BRAIN ---
                with st.spinner("Running Reconciliation Audit..."):
                    simulated_db = {
                        extracted_data.get("invoice_number", "UNKNOWN"): {
                            "expected_total": expected_total,
                            "approved_fees": []
                        }
                    }
                    audit_report = run_audit(extracted_data, simulated_db)
                
                st.markdown("### 📊 Audit Results")
                
                if audit_report["status"] == "DISPUTE REQUIRED":
                    st.error(f"Status: {audit_report['status']} (Variance: ${audit_report['total_disputed_amount']})")
                    
                    for flag in audit_report["flags"]:
                        st.warning(flag)
                    
                    # --- PHASE 3: THE VOICE ---
                    st.markdown("### ✉️ Auto-Drafted Dispute Email")
                    with st.spinner("Drafting carrier communication..."):
                        invoice_details = {
                            "carrier_name": extracted_data.get("carrier_name", "Carrier"),
                            "invoice_number": extracted_data.get("invoice_number", "UNKNOWN")
                        }
                        email_draft = generate_dispute_email(audit_report, invoice_details)
                        
                        # We use the file name as a unique key so the text boxes don't overlap
                        st.text_area(f"Copy and send this to your carrier rep for {uploaded_file.name}:", value=email_draft, height=250, key=uploaded_file.name)

                else:
                    st.success(f"Status: {audit_report['status']}")
                    st.info("Invoice matches internal records. Approved for payment.")

            except Exception as e:
                st.error(f"Pipeline Failed for {uploaded_file.name}: {e}")
                
            finally:
                # Clean up the temporary file behind the scenes
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
            
            # Put a clean visual divider before starting the next invoice
            st.markdown("---")