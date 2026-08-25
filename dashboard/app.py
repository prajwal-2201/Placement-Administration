import sys
import os
import streamlit as st
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.database.db import get_db_connection
from src.replanner.disruption import apply_disruption
from src.replanner.impact import calculate_impact
from src.replanner.replan import perform_replan
from src.scheduler.validator import validate_schedule

st.set_page_config(page_title="Placement Administration", layout="wide", initial_sidebar_state="expanded")

# --- DATA FETCHING ---
@st.cache_data(ttl=5)
def get_dashboard_data():
    conn = get_db_connection()
    metrics = {
        'completed': conn.execute("SELECT COUNT(*) FROM interviews WHERE status='COMPLETED'").fetchone()[0],
        'upcoming': conn.execute("SELECT COUNT(*) FROM interviews WHERE status='SCHEDULED'").fetchone()[0],
        'rooms': conn.execute("SELECT COUNT(DISTINCT room_id) FROM interviews WHERE status='SCHEDULED'").fetchone()[0],
        'panels': conn.execute("SELECT COUNT(DISTINCT panel_id) FROM interviews WHERE status='SCHEDULED'").fetchone()[0],
    }
    df = pd.read_sql_query("""
        SELECT interview_id as ID, student_id as Student, company_id as Company, 
               room_id as Room, panel_id as Panel, date as Date, 
               start_time as Start, end_time as End, status as Status
        FROM interviews ORDER BY date, start_time
    """, conn)
    
    entities = {
        'rooms': [r[0] for r in conn.execute("SELECT room_id FROM rooms WHERE status='ACTIVE'").fetchall()],
        'panels': [r[0] for r in conn.execute("SELECT panel_id FROM panels WHERE status='ACTIVE'").fetchall()],
        'companies': [r[0] for r in conn.execute("SELECT company_id FROM companies").fetchall()],
        'students': [r[0] for r in conn.execute("SELECT student_id FROM students WHERE status='ACTIVE'").fetchall()]
    }
    conn.close()
    return metrics, df, entities

metrics, schedule_df, entities = get_dashboard_data()

# --- HEADER ---
st.title("Placement Administration")
st.subheader("Interview Scheduling & Resource Management")

st.info("System Status: Operational. Day 3 schedules are active.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Completed Interviews", metrics["completed"])
col2.metric("Upcoming Interviews", metrics["upcoming"])
col3.metric("Active Rooms", metrics["rooms"])
col4.metric("Active Panels", metrics["panels"])

st.divider()

tab1, tab2 = st.tabs(["Incident Management", "Schedule View"])

with tab2:
    st.subheader("Master Schedule")
    st.dataframe(schedule_df, use_container_width=True, hide_index=True)

with tab1:
    st.subheader("Report Incident")
    st.write("Select the operational issue to analyze impact and generate a revised schedule.")
    
    col_disrupt, col_replan = st.columns([1, 2], gap="large")
    
    with col_disrupt:
        disruption_type = st.selectbox(
            "Incident Type", 
            ["ROOM_UNAVAILABLE", "PANEL_DROPOUT", "STUDENT_WITHDRAWAL", "COMPANY_DELAY"]
        )
        
        target_id = None
        details = {}
        
        if disruption_type == "ROOM_UNAVAILABLE":
            target_id = st.selectbox("Select Room", entities['rooms'])
        elif disruption_type == "PANEL_DROPOUT":
            target_id = st.selectbox("Select Panel", entities['panels'])
        elif disruption_type == "STUDENT_WITHDRAWAL":
            target_id = st.selectbox("Select Student", entities['students'])
        elif disruption_type == "COMPANY_DELAY":
            target_id = st.selectbox("Select Company", entities['companies'])
            delay = st.number_input("Delay in Minutes", min_value=15, max_value=300, step=15, value=60)
            details = {"delay_minutes": delay}
            
        if st.button("Analyze Impact & Replan", type="primary", use_container_width=True):
            if not target_id:
                st.error("Please select a target for the incident.")
            else:
                st.session_state['run_replan'] = {
                    "type": disruption_type,
                    "target_id": target_id,
                    "details": details
                }
                
    with col_replan:
        if 'run_replan' in st.session_state:
            incident = st.session_state['run_replan']
            parsed_disruptions = [incident]
            
            st.success(f"Registered Incident: {incident['type']} for {incident['target_id']}")
            
            with st.spinner("Evaluating schedule impact..."):
                all_impacted = []
                for d in parsed_disruptions:
                    d_id = apply_disruption(d['type'], d['target_id'], d.get('details', {}))
                    impacted = calculate_impact(d_id)
                    all_impacted.extend(impacted)
                    
                unique_impacted = {i['interview_id']: i for i in all_impacted}.values()
                unique_impacted = list(unique_impacted)
                
            st.info(f"Impact Assessment: {len(unique_impacted)} scheduled interviews are affected.")
            
            if len(unique_impacted) > 0:
                with st.spinner("Generating revised schedule..."):
                    replanned, unscheduled = perform_replan(unique_impacted)
                    is_valid = validate_schedule()
                    
                    if is_valid:
                        st.success("Rescheduling complete. Constraints verified.")
                        st.subheader("Schedule Adjustments")
                        
                        for r in replanned:
                            st.write(f"**Interview ID:** {r['interview_id']}")
                            st.write(f"- Student: {r.get('student_id', 'Unknown')} | Company: {r.get('company_id', 'Unknown')}")
                            
                            if r['old_room'] != r['new_room']:
                                st.write(f"- **Room:** {r['old_room']} ➔ {r['new_room']}")
                            else:
                                st.write(f"- **Room:** {r['old_room']} (Unchanged)")
                                
                            if r['old_time'] != r['new_time']:
                                st.write(f"- **Time:** {r['old_time']} ➔ {r['new_time']}")
                            else:
                                st.write(f"- **Time:** {r['old_time']} (Unchanged)")
                            st.divider()
                            
                        if unscheduled:
                            st.error(f"{len(unscheduled)} interviews could not be automatically rescheduled due to capacity constraints and require manual review.")
                    else:
                        st.error("Validation Error: The generated schedule does not meet all constraints.")
            else:
                st.info("The reported incident does not impact the current schedule.")
        
            if st.button("Clear Results"):
                del st.session_state['run_replan']
                st.rerun()
        else:
            st.write("Awaiting incident report...")
