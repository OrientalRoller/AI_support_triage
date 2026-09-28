# AI Support Triage

An automated, RAG-enabled technical support triage pipeline. This system ingests live GitHub issues, uses a local Llama 3 model and a ChromaDB vector database to categorize tickets and hypothesize root causes based on historical data, and presents the processed tickets in a Streamlit dashboard for manager review.

> **🚧 Infrastructure Notice: Docker Status**
> The Docker containerization (`docker-compose.yml`) for this pipeline is currently undergoing maintenance due to environment caching and isolated network bridging issues between Streamlit and MongoDB. We are actively working on a fix and will add full Docker support in a later update. In the meantime, please follow the [Local Setup Guide](#local-setup-guide) below to run the pipeline directly on your host machine.

---

## System Architecture

- **Data Ingestion:** Python script using the GitHub REST API to fetch live issues (currently tracking `ollama/ollama`), preventing duplicates via MongoDB `find_one` checks.
- **Vector Knowledge Base (RAG):** Persistent ChromaDB storing previously resolved tickets. The engine queries this database to inject similar historical resolutions into the LLM prompt.
- **AI Triage Engine:** Local Llama 3 model (via Ollama) enforcing a strict JSON schema output to assign severity and category, and to generate a Bash/Python remediation script.
- **Database & UI:** MongoDB handles asynchronous state transitions (`pending_triage` → `awaiting_approval`), dynamically visualized in a Streamlit web application.

---

## Local Setup Guide

### 1. Prerequisites

Ensure the following are installed and running on your host machine:

- Python 3.10+
- **MongoDB:** running locally on the default port (`localhost:27017`)
- **Ollama:** installed and running locally

### 2. Environment Configuration

Clone the repository and set up an isolated Python environment:

```bash
git clone https://github.com/YOUR-USERNAME/AI_support_triage.git
cd AI_support_triage

# Initialize and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install core dependencies (Streamlit, PyMongo, ChromaDB, Requests, Ollama)
pip install -r requirements.txt
```

### 3. Ensure Local Database Binding

Because Docker is temporarily disabled, make sure your `.env` file (or terminal environment) targets your local machine's database:

```ini
MONGO_URI="mongodb://localhost:27017/"
```

### 4. Pull the Local LLM

Ensure Ollama has the Llama 3 model downloaded and ready for inference:

```bash
ollama pull llama3
```

---

## Execution Flow

Execute the pipeline modules sequentially from the terminal to process and view the tickets.

### Step 1: Ingest Live Tickets

Pulls fresh, deduplicated issues from the GitHub API and stages them in MongoDB with the status `pending_triage`.

```bash
python3 fetch_tickets.py
```

### Step 2: Run the RAG Triage Engine

Triggers Llama 3 to analyze the pending tickets against historical ChromaDB data. The AI updates the MongoDB records with severity, category, and automated remediation scripts.

```bash
python3 triage_engine.py
```

### Step 3: Launch the Manager Dashboard

Starts the Streamlit interface to view the categorized L1/L2 tickets awaiting human approval. Run it with the Python module flag to avoid executable path issues.

```bash
python3 -m streamlit run support_dashboard.py
```
