import json
from src.database.db import get_db_connection
from src.scheduler.validator import time_to_minutes

def calculate_impact(disruption_id):
    """
    Given a disruption ID, find all scheduled interviews that are now invalid.
    """
    conn = get_db_connection()
    disruption = conn.execute("SELECT * FROM disruptions WHERE disruption_id = ?", (disruption_id,)).fetchone()
    if not disruption:
        print("Disruption not found.")
        return []
        
    d_type = disruption['type']
    target = disruption['target_id']
    details = json.loads(disruption['details'])
    
    interviews = [dict(row) for row in conn.execute("SELECT * FROM interviews WHERE status='SCHEDULED'").fetchall()]
    
    impacted = []
    
    for inv in interviews:
        if d_type == 'ROOM_UNAVAILABLE' and inv['room_id'] == target:
            impacted.append(inv)
        elif d_type == 'PANEL_DROPOUT' and inv['panel_id'] == target:
            impacted.append(inv)
        elif d_type == 'STUDENT_WITHDRAWAL' and inv['student_id'] == target:
            impacted.append(inv)
        elif d_type == 'COMPANY_DELAY' and inv['company_id'] == target:
            delay_mins = details.get('delay_minutes', 0)
            arrival_day = details.get('day', 'Day 1')
            if inv['date'] == arrival_day:
                # 9:00 AM + delay
                new_start = time_to_minutes("09:00") + delay_mins
                if time_to_minutes(inv['start_time']) < new_start:
                    impacted.append(inv)
                    
    conn.close()
    
    # Provide summary
    students = set(i['student_id'] for i in impacted)
    companies = set(i['company_id'] for i in impacted)
    
    print(f"--- IMPACT ANALYSIS ---")
    print(f"Cause: {d_type} ({target})")
    print(f"Affected Interviews: {len(impacted)}")
    print(f"Affected Students: {len(students)}")
    print(f"Affected Companies: {len(companies)}")
    
    return impacted
