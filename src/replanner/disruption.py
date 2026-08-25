import sqlite3
import uuid
import json
from src.database.db import get_db_connection

def apply_disruption(disruption_type, target_id, details_dict):
    """
    Registers a disruption in the database.
    Types: COMPANY_DELAY, PANEL_DROPOUT, STUDENT_WITHDRAWAL, ROOM_UNAVAILABLE
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    d_id = f"DIS-{uuid.uuid4().hex[:8]}"
    
    # Insert disruption log
    cur.execute(
        "INSERT INTO disruptions (disruption_id, type, target_id, details) VALUES (?, ?, ?, ?)",
        (d_id, disruption_type, target_id, json.dumps(details_dict))
    )
    
    # Apply state changes to the database entities so the solver sees them as unavailable
    if disruption_type == 'ROOM_UNAVAILABLE':
        cur.execute("UPDATE rooms SET status = 'UNAVAILABLE' WHERE room_id = ?", (target_id,))
    elif disruption_type == 'STUDENT_WITHDRAWAL':
        cur.execute("UPDATE students SET status = 'WITHDRAWN' WHERE student_id = ?", (target_id,))
    elif disruption_type == 'PANEL_DROPOUT':
        cur.execute("UPDATE panels SET status = 'UNAVAILABLE' WHERE panel_id = ?", (target_id,))
    elif disruption_type == 'COMPANY_DELAY':
        # Handled in the replanning logic (interviews before the delay are invalid)
        pass
        
    conn.commit()
    conn.close()
    print(f"Disruption {d_id} logged: {disruption_type} for {target_id}")
    return d_id
