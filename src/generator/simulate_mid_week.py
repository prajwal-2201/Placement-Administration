import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.database.db import get_db_connection

def simulate_mid_week():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Mark Day 1 and Day 2 as COMPLETED
    cur.execute("UPDATE interviews SET status = 'COMPLETED' WHERE date IN ('Day 1', 'Day 2')")
    
    # Ensure Day 3 and Day 4 are SCHEDULED
    cur.execute("UPDATE interviews SET status = 'SCHEDULED' WHERE date IN ('Day 3', 'Day 4')")
    
    conn.commit()
    conn.close()
    
    print("Database updated: Day 1 and Day 2 interviews marked as COMPLETED.")
    print("System is now ready to simulate starting on Wednesday (Day 3).")

if __name__ == '__main__':
    simulate_mid_week()
