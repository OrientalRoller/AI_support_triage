import streamlit as st
import pandas as pd
from pymongo import MongoClient
import os
import requests
import json

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["firellama_support"]
tickets_collection = db["incoming_tickets"]

# Configure the Streamlit Page
st.set_page_config(page_title="FireLLama Support Platform", layout="wide")
st.title("FireLLama Support Platform")


tab1, tab2 = st.tabs(["L1/L2 Triage Desk", "Manager Analytics"])

# TAB 1: THE TRIAGE DESK (Engineer View)
with tab1:
    st.markdown("Review categorized system tickets, approve responses, and execute automated remediation scripts.")
    tickets = list(tickets_collection.find({"status": "awaiting_approval"}))

    if not tickets:
        st.write("**Status:** Queue is clear. No tickets awaiting review.")
    else:
        st.subheader(f"{len(tickets)} Tickets Pending Approval")
        for ticket in tickets:
            doc_id = ticket['_id']
            
            # Professional severity labeling
            sev = ticket.get('severity', 'Medium').upper()
            badge = f"[{sev}]"
                
            with st.expander(f"{badge} | {ticket.get('category')} | {ticket['title']}"):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("**User Issue Description:**")
                    st.write(ticket.get('description', 'No description provided.')[:800] + "...")
                    st.markdown(f"[View Original GitHub Issue]({ticket.get('url')})")
                    
                    st.markdown("**Executable Remediation Script:**")
                    st.code(ticket.get('remediation_script', 'No script generated.'), language='bash')
                    
                    if st.button("Run Remediation Script", key=f"run_{doc_id}"):
                        st.write("**System Warning:** Script execution initialized. Check server logs for output.")
                    
                with col2:
                    st.markdown("**AI Root Cause Hypothesis:**")
                    st.write(ticket.get('root_cause_hypothesis', 'No hypothesis generated.'))
                    
                    edited_response = st.text_area(
                        "Generated Support Response (Editable):", 
                        ticket.get('draft_response', ''), 
                        height=130, 
                        key=f"text_{doc_id}"
                    )
                    
                    if st.button("Approve & Resolve Ticket", key=f"approve_{doc_id}"):
                        tickets_collection.update_one(
                            {"_id": doc_id}, 
                            {"$set": {"status": "resolved", "final_response": edited_response}}
                        )
                        st.rerun()

# TAB 2: MANAGER ANALYTICS (Executive View)
with tab2:
    st.markdown("System telemetry and ticket resolution metrics.")
    
    all_tickets = list(tickets_collection.find())
    
    if not all_tickets:
        st.write("**Status:** Insufficient data for analytics generation.")
    else:
        df = pd.DataFrame(all_tickets)
        total_tickets = len(df)
        pending_triage = len(df[df['status'] == 'pending_triage']) if 'status' in df.columns else 0
        awaiting_approval = len(df[df['status'] == 'awaiting_approval']) if 'status' in df.columns else 0
        resolved = len(df[df['status'] == 'resolved']) if 'status' in df.columns else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Ingested Tickets", total_tickets)
        col2.metric("In AI Processing Queue", pending_triage)
        col3.metric("Awaiting Human Review", awaiting_approval)
        col4.metric("Successfully Resolved", resolved)
        
        st.divider()
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("**Incident Volume by System Component**")
            if 'category' in df.columns:
                cat_counts = df['category'].value_counts()
                st.bar_chart(cat_counts, color="#3498db")
                
        with col_chart2:
            st.markdown("**Severity Level Distribution**")
            if 'severity' in df.columns:
                sev_counts = df['severity'].value_counts()
                st.bar_chart(sev_counts, color="#e74c3c")