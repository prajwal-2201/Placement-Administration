import os
from src.database.db import get_db_connection

def time_to_minutes(time_str):
    """Convert 'HH:MM' to minutes since midnight."""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m

def check_overlaps(interviews, entity_key, entity_name):
    """
    Checks for overlapping interviews grouped by the given entity_key.
    Returns a list of errors if overlaps exist.
    """
    errors = []
    
    # Group interviews by entity and day
    grouped = {}
    for inv in interviews:
        key = (inv[entity_key], inv['date'])
        grouped.setdefault(key, []).append(inv)
        
    for key, inv_list in grouped.items():
        entity_id, day = key
        # Sort by start time
        inv_list.sort(key=lambda x: time_to_minutes(x['start_time']))
        
        for i in range(len(inv_list) - 1):
            curr = inv_list[i]
            nxt = inv_list[i + 1]
            
            curr_end = time_to_minutes(curr['end_time'])
            nxt_start = time_to_minutes(nxt['start_time'])
            
            if curr_end > nxt_start:
                errors.append(f"Overlap for {entity_name} {entity_id} on {day}: "
                              f"{curr['start_time']}-{curr['end_time']} vs {nxt['start_time']}-{nxt['end_time']}")
    
    return errors

def validate_schedule():
    conn = get_db_connection()
    interviews = [dict(row) for row in conn.execute("SELECT * FROM interviews WHERE status='SCHEDULED'").fetchall()]
    shortlists = set((row['student_id'], row['company_id']) for row in conn.execute("SELECT student_id, company_id FROM shortlists").fetchall())
    conn.close()

    if not interviews:
        print("Warning: No scheduled interviews found in the database.")
        return True

    print(f"Validating {len(interviews)} interviews...")
    
    all_errors = []

    # 1. Check Student Overlaps
    student_errors = check_overlaps(interviews, 'student_id', 'Student')
    all_errors.extend(student_errors)

    # 2. Check Room Overlaps
    room_errors = check_overlaps(interviews, 'room_id', 'Room')
    all_errors.extend(room_errors)

    # 3. Check Panel Overlaps
    panel_errors = check_overlaps(interviews, 'panel_id', 'Panel')
    all_errors.extend(panel_errors)

    # 4. Check Eligibility Constraint
    for inv in interviews:
        if (inv['student_id'], inv['company_id']) not in shortlists:
            all_errors.append(f"Eligibility violation: Student {inv['student_id']} not shortlisted for Company {inv['company_id']}.")

    if all_errors:
        print(f"VALIDATION FAILED! Found {len(all_errors)} constraint violations:")
        for err in all_errors[:20]:
            print(f" - {err}")
        if len(all_errors) > 20:
            print(f" ... and {len(all_errors) - 20} more errors.")
        return False
    else:
        print("VALIDATION SUCCESSFUL! The schedule is 100% mathematically valid.")
        print("- 0 Student overlaps")
        print("- 0 Room overlaps")
        print("- 0 Panel overlaps")
        print("- 0 Eligibility violations")
        return True

if __name__ == '__main__':
    validate_schedule()
