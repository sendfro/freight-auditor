import json

def run_audit(extracted_invoice, internal_database):
    print(f"[*] Auditing Invoice #{extracted_invoice['invoice_number']} from {extracted_invoice['carrier_name']}...")
    
    invoice_num = extracted_invoice["invoice_number"]
    
    # 1. Check if we even have a record for this shipment
    if invoice_num not in internal_database:
        return {"status": "FAILED", "reason": "No internal record found for this invoice."}
        
    expected_data = internal_database[invoice_num]
    actual_total = extracted_invoice["total_billed_amount"]
    expected_total = expected_data["expected_total"]
    
    discrepancies = []
    
    # 2. Check for Total Amount Discrepancy
    if actual_total > expected_total:
        overcharge = actual_total - expected_total
        discrepancies.append(f"OVERCHARGE DETECTED: Billed ${actual_total}, but expected ${expected_total}. Variance: ${overcharge}")
        
    # 3. Check for unauthorized line items (Phantom Fees)
    # We look for keywords that logistics managers hate
    red_flag_keywords = ["liftgate", "residential", "shipping costs", "fuel surcharge", "expedited"]
    
    for item in extracted_invoice["line_items"]:
        description = item["description"].lower()
        for flag in red_flag_keywords:
            if flag in description and flag not in expected_data["approved_fees"]:
                 discrepancies.append(f"UNAUTHORIZED FEE DETECTED: {item['description']} for ${item['charge_amount']}")

    # 4. Final Verdict
    if len(discrepancies) > 0:
        return {
            "status": "DISPUTE REQUIRED", 
            "total_disputed_amount": actual_total - expected_total,
            "flags": discrepancies
        }
    else:
        return {"status": "CLEAN", "message": "Invoice matches internal records. Approved for payment."}

# --- Execution ---
if __name__ == "__main__":
    
    # This is the exact data your Extractor just pulled from the DHL image!
    simulated_ai_output = {
      "carrier_name": "DHL EXPRESS",
      "invoice_number": "5559-789",
      "total_billed_amount": 1150.0,
      "line_items": [
        {"description": "Populated Printed Circuit Board", "charge_amount": 1000.0},
        {"description": "Laser Imaging Assembly", "charge_amount": 100.0},
        {"description": "Total Shipping Costs", "charge_amount": 50.0}
      ]
    }
    
    # This simulates the logistics manager's Excel sheet. 
    # Notice we expect the total to be 1100, and we did NOT approve extra shipping costs.
    simulated_internal_db = {
        "5559-789": {
            "expected_total": 1100.0,
            "approved_fees": [] 
        }
    }
    
    print("\n--- INITIATING FREIGHT AUDIT ---")
    audit_report = run_audit(simulated_ai_output, simulated_internal_db)
    
    print("\n--- AUDIT REPORT ---")
    print(json.dumps(audit_report, indent=2))