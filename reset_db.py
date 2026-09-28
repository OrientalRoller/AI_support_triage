from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
# Updated to the new FireLLama persona
db = client["firellama_support"]

# Drop the collections to wipe the slate clean
db.incoming_tickets.drop()
db.resolved_tickets.drop() # Also clears the vector DB sync state if it exists

print("Database successfully wiped! You are ready to start fresh with FireLLama.")