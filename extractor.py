import streamlit as st
import base64
import json
import os
from google import genai
from google.genai import types

# --- PASTE YOUR API KEY HERE JUST FOR THIS TEST ---
my_api_key = st.secrets["GEMINI_API_KEY"]

client = genai.Client(api_key=my_api_key)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_invoice_data(image_path):
    print(f"[*] Reading document: {image_path}...")
    encoded_image = encode_image(image_path)
    
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "carrier_name": {"type": "STRING"},
            "invoice_number": {"type": "STRING"},
            "total_billed_amount": {"type": "NUMBER"},
            "line_items": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "description": {"type": "STRING"},
                        "charge_amount": {"type": "NUMBER"}
                    }
                }
            }
        }
    }

    prompt = "Extract the carrier details, invoice number, total amounts, and every single line item charge. Output ONLY valid JSON matching the schema."

    print("[*] Processing through AI Vision Model... please wait.")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Part.from_bytes(data=base64.b64decode(encoded_image), mime_type='image/jpeg'),
            prompt
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.0 
        ),
    )
    
    return json.loads(response.text)

if __name__ == "__main__":
    dummy_invoice_path = "carrier_invoice_sample.jpg" 
    
    try:
        data = extract_invoice_data(dummy_invoice_path)
        print("\n[+] Success! Here is the extracted data:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"\n[-] Something went wrong: {e}")