import os
import requests
import time
import re

BASE_URL = "http://localhost:8000"
CV_DIR = "/mnt/z/CV/Frind_CV"

def register_customer(email, password, name):
    print(f"\n--- Registering Customer: {name} ({email}) ---")
    url = f"{BASE_URL}/auth/register"
    payload = {
        "email": email,
        "password": password,
        "name": name,
        "role": "CUSTOMER"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 201:
        print(f"Successfully registered {name}")
    elif response.status_code == 400 and "Email already registered" in response.text:
        print(f"Customer {name} already registered")
    else:
        print(f"Failed to register {name}: {response.text}")

def login_customer(email, password):
    print(f"Logging in {email}...")
    url = f"{BASE_URL}/auth/login"
    payload = {
        "email": email,
        "password": password
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Login successful")
        return response.json().get("access_token")
    else:
        print(f"Login failed: {response.text}")
        return None

def upload_cv(token, file_path):
    print(f"Uploading CV: {os.path.basename(file_path)}...")
    url = f"{BASE_URL}/data/upload"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/pdf")}
        response = requests.post(url, headers=headers, files=files)
        
    if response.status_code == 200:
        file_id = response.json().get("file_id")
        print(f"Successfully uploaded CV. File ID: {file_id}")
        return file_id
    else:
        print(f"Failed to upload CV: {response.text}")
        return None

def process_cv(token, file_id):
    print(f"Processing CV chunks and storing in ChromaDB: {file_id}...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "file_id": file_id,
        "chunk_size": 500,
        "overlap_size": 50
    }
    # Canonical indexing endpoint (same as frontend onboarding).
    # Falls back to /data/process (which now also indexes) for older backends.
    for url in (f"{BASE_URL}/nlp/index", f"{BASE_URL}/data/process"):
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"Successfully processed CV via {url}.")
            return True
        print(f"Failed to process CV via {url}: {response.text}")
    return False

def clean_name(filename):
    # Remove extension and clean up
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    name = name.strip()
    
    # Fallback if name is empty
    if not name:
        name = "Candidate"
    
    # Generate email
    email = name.replace(" ", ".").lower() + "@gmail.com"
    return name, email

def main():
    if not os.path.exists(CV_DIR):
        print(f"Directory {CV_DIR} not found.")
        return

    password = "123"
    
    files = [f for f in os.listdir(CV_DIR) if f.lower().endswith('.pdf')]
    print(f"Found {len(files)} PDF files.")
    
    for filename in files:
        file_path = os.path.join(CV_DIR, filename)
        name, email = clean_name(filename)
        
        # 1. Register
        register_customer(email, password, name)
        
        # 2. Login
        token = login_customer(email, password)
        if not token:
            continue
            
        # 3. Upload
        file_id = upload_cv(token, file_path)
        if not file_id:
            continue
            
        # 4. Process (Extract, chunk, ChromaDB)
        process_cv(token, file_id)
        
        # Sleep to avoid rate limits or database lock issues
        time.sleep(2)
        
    print("\n--- Seeding Candidates Complete ---")

if __name__ == "__main__":
    main()
