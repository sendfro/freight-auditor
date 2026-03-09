import streamlit as st
import os
from google import genai

# --- PASTE YOUR API KEY HERE ---
my_api_key = st.secrets["GEMINI_API_KEY"]

client = genai.Client(api_key=my_api_key)

def generate_dispute_email(audit_report, invoice_details):
    print(f"[*] Drafting dispute email to {invoice_details['carrier_name']} for Invoice #{invoice_details['invoice_number']}...")
    
    # This prompt is the strict instruction set for how the AI should behave
    prompt = f"""
    You are a strict but highly professional Logistics Manager for our company.
    Write an email to our carrier account representative.
    
    Carrier: {invoice_details['carrier_name']}
    Invoice Number: {invoice_details['invoice_number']}
    Total Disputed Amount: ${audit_report['total_disputed_amount']}
    
    Reasons for dispute:
    {chr(10).join(audit_report['flags'])}
    
    Instructions:
    1. Be direct and polite, but absolutely firm.
    2. Clearly state the invoice number and the exact disputed amount in the first sentence.
    3. Explain exactly why the fee is unauthorized based on the provided reasons.
    4. Demand a revised invoice or a credit memo immediately.
    5. Keep it concise. Do not include subject lines like [Subject: ...], just write the email body.
    6. Sign off as "Automated Freight Agent".
    """

    print("[*] Generating text via AI...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    return response.text

# --- Execution ---
if __name__ == "__main__":
    
    # Simulated data from our Extractor (Module 2)
    simulated_invoice_details = {
        "carrier_name": "DHL EXPRESS",
        "invoice_number": "5559-789"
    }
    
    # Simulated data from our Auditor (Module 3)
    simulated_audit_report = {
        "status": "DISPUTE REQUIRED", 
        "total_disputed_amount": 50.0,
        "flags": [
            "OVERCHARGE DETECTED: Billed $1150.0, but expected $1100.0. Variance: $50.0",
            "UNAUTHORIZED FEE DETECTED: Total Shipping Costs for $50.0"
        ]
    }
    
    print("\n--- INITIATING DISPUTE GENERATOR ---")
    email_draft = generate_dispute_email(simulated_audit_report, simulated_invoice_details)
    
    print("\n================ DRAFTED EMAIL ================\n")
    print(email_draft)
    print("\n===============================================\n")