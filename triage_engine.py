import time
import json
import ollama
import chromadb
import os
import requests
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["firellama_support"]
tickets_collection = db["incoming_tickets"]

chroma_client = chromadb.PersistentClient(path="./chroma_db")
vector_collection = chroma_client.get_or_create_collection(name="resolved_tickets")

def sync_historical_knowledge():
    """Extracts resolved tickets from MongoDB and upserts them into the Vector DB."""
    resolved_tickets = list(tickets_collection.find({"status": "resolved"}))
    if not resolved_tickets:
        return 0
    
    docs, metadatas, ids = [], [], []
    
    for t in resolved_tickets:
        doc_id = str(t["_id"])
        ids.append(doc_id)
        docs.append(t.get("title", "") + " " + t.get("description", ""))
        metadatas.append({
            "resolution": t.get("final_response", "No response recorded"),
            "script": t.get("remediation_script", "")
        })
        
    vector_collection.upsert(documents=docs, metadatas=metadatas, ids=ids)
    return len(resolved_tickets)

def get_rag_context(ticket_title, ticket_description):
    """Searches the Vector DB for the top 2 most similar past issues."""
    if vector_collection.count() == 0:
        return "No historical context available in the knowledge base."
        
    query_text = f"{ticket_title} {ticket_description}"
    results = vector_collection.query(query_texts=[query_text], n_results=2)
    
    if not results['documents'] or len(results['documents'][0]) == 0:
        return "No strictly matching historical context found."
        
    historical_context = "Historical Similar Tickets and Approved Solutions:\n"
    for idx, doc in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][idx]
        historical_context += f"- Past Issue Synopsis: {doc[:200]}...\n"
        historical_context += f"  Approved Past Resolution: {meta['resolution']}\n"
        historical_context += f"  Executed Past Script: {meta['script']}\n\n"
        
    return historical_context

def triage_ticket(ticket):
    print(f"[PROCESS] Analyzing Support Ticket: {ticket.get('title', 'Unknown Title')}")
    
    # Retrieve dynamic historical context (RAG)
    rag_context = get_rag_context(ticket.get("title", ""), ticket.get("description", ""))
    
    prompt = f"""
    You are a Senior Level 3 Technical Support Engineer at FireLLama, a custom software and AI development company.
    Read the following customer issue and output a strictly formatted JSON response.
    
    Ticket Title: {ticket.get('title', '')}
    Ticket Body: {ticket.get('description', '')}
    
    {rag_context}
    
    Based on the historical context (if provided) and your technical knowledge, respond ONLY with a JSON object using this exact format:
    {{
        "category": "Pick one: [Application UI, Backend/API, Database, AI Model/Integration, Infrastructure, Configuration, Unknown]",
        "severity": "Pick one: [Low, Medium, High, Critical]",
        "root_cause_hypothesis": "One sentence guessing the underlying technical issue. Reference historical solutions if applicable.",
        "draft_response": "Write a polite, technical 2-sentence response to the user offering a debugging step.",
        "remediation_script": "Write a single, executable bash command or python snippet to investigate or fix this issue."
    }}
    """

    response = ollama.chat(
        model='llama3',
        messages=[{'role': 'user', 'content': prompt}],
        format='json'
    )
    
    try:
        triage_data = json.loads(response['message']['content'])
        
        tickets_collection.update_one(
            {"_id": ticket["_id"]},
            {"$set": {
                "category": triage_data.get("category", "Unknown"),
                "severity": triage_data.get("severity", "Medium"),
                "root_cause_hypothesis": triage_data.get("root_cause_hypothesis", ""),
                "draft_response": triage_data.get("draft_response", ""),
                "remediation_script": triage_data.get("remediation_script", "echo 'No automated script generated.'"),
                "status": "awaiting_approval"
            }}
        )
        print(f"[SUCCESS] Classification complete: {triage_data.get('severity')} | {triage_data.get('category')}")
        
    except Exception as e:
        print(f"[ERROR] System Error - LLM Parsing Failed: {e}")
        tickets_collection.update_one(
            {"_id": ticket["_id"]},
            {"$set": {"status": "triage_failed"}}
        )

def run_triage_batch():
    print("[INIT] FireLLama Auto-Triage Engine (RAG-Enabled) Initialized.")
    
    # Sync database before beginning batch
    synced_count = sync_historical_knowledge()
    print(f"[SYSTEM] Synchronized {synced_count} resolved tickets to Vector Database.")
    print("[SYSTEM] Scanning database for pending tickets...")
    
    while True:
        pending_ticket = tickets_collection.find_one({"status": "pending_triage"})
        
        if pending_ticket:
            triage_ticket(pending_ticket)
            time.sleep(2) 
        else:
            print("[INFO] Batch processing complete. No pending tickets remaining. Terminating process.")
            break

if __name__ == "__main__":
    run_triage_batch()