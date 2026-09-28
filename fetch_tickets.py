import os
import requests
import json
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["firellama_support"]
tickets_collection = db["incoming_tickets"]

# 2. Target a real AI/Software repository to match FireLLama's persona
# Switched from aws/aws-cli (Cloud) to ollama/ollama (AI/Custom Software)
REPO = "ollama/ollama"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO}/issues?state=open&per_page=15"

def fetch_real_issues():
    print(f"[INIT] Fetching live AI and software support issues from {REPO}...")
    
    # Hit the public GitHub API
    response = requests.get(GITHUB_API_URL)
    
    if response.status_code != 200:
        print(f"[ERROR] Failed to connect to GitHub API. Status: {response.status_code}")
        return

    issues = response.json()
    new_tickets = 0
    
    for issue in issues:
        # Skip pull requests, we only want actual bug reports/issues
        if 'pull_request' in issue:
            continue
            
        ticket_id = issue['id']
        
        # Deduplication: Don't process tickets we already have in MongoDB
        if tickets_collection.find_one({"ticket_id": ticket_id}):
            continue
            
        # Clean the data and cap the length so we don't overload Llama 3 later
        ticket_data = {
            "ticket_id": ticket_id,
            "title": issue.get('title', ''),
            "description": issue.get('body', '')[:2000] if issue.get('body') else "No description", 
            "url": issue.get('html_url', ''),
            "status": "pending_triage"
        }
        
        # Insert into database
        tickets_collection.insert_one(ticket_data)
        new_tickets += 1
        print(f"[SUCCESS] Ingested Ticket: {ticket_data['title'][:50]}...")
        
    print(f"\n[SYSTEM] Phase 1 Complete: Successfully ingested {new_tickets} new live tickets into MongoDB.")

if __name__ == "__main__":
    fetch_real_issues()