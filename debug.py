import os
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["firellama_support"]
tickets = list(db["incoming_tickets"].find())

print(f"Total tickets in database: {len(tickets)}")
for t in tickets:
    print(f"Status: '{t.get('status')}' | Title: {t.get('title')[:40]}...")