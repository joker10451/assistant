import os
from dotenv import load_dotenv, find_dotenv
import google.genai as genai

load_dotenv(find_dotenv())

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("No API key found")
    exit()

client = genai.Client(api_key=api_key)

try:
    print("Listing models...")
    # New SDK way to list models might differ, let's try standard approach or check documentation logic
    # In new SDK it is client.models.list() usually?
    # Based on error message "Call ListModels"
    
    # We will try to iterate and print
    # Note: google-genai SDK usage: client.models.list()
    
    pager = client.models.list()
    for model in pager:
        print(f"Model: {model.name}")
        print(f"  Supported generation methods: {model.supported_generation_methods}")
        
except Exception as e:
    print(f"Error: {e}")
