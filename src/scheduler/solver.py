import sys
import os
from ortools.sat.python import cp_model
from src.database.db import get_db_connection
import json
import uuid

DAYS = ['Day 1', 'Day 2', 'Day 3', 'Day 4']
SLOTS_PER_DAY = 16  # 9:00 AM to 5:00 PM in 30 min increments
TOTAL_SLOTS = len(DAYS) * SLOTS_PER_DAY

def load_data():
    conn = get_db_connection()
    students = [dict(row) for row in conn.execute("SELECT * FROM students").fetchall()]
    companies = [dict(row) for row in conn.execute("SELECT * FROM companies").fetchall()]
    # To make this tractable for a fast demo, limit to top 1500 shortlists by CGPA
    shortlists = [dict(row) for row in conn.execute('''
        SELECT s.*, st.cgpa 
        FROM shortlists s 
        JOIN students st ON s.student_id = st.student_id
        ORDER BY st.cgpa DESC
        LIMIT 500
    ''').fetchall()]
    rooms = [dict(row) for row in conn.execute("SELECT * FROM rooms").fetchall()]
    panels = [dict(row) for row in conn.execute("SELECT * FROM panels").fetchall()]
    conn.close()
    return students, companies, shortlists, rooms, panels

def generate_schedule():
    print("Loading data...")
    students, companies, shortlists, rooms, panels = load_data()
    
    company_dict = {c['company_id']: c for c in companies}
    panels_by_company = {}
    for p in panels:
        panels_by_company.setdefault(p['company_id'], []).append(p['panel_id'])

    model = cp_model.CpModel()
    
    print("Creating variables (using Optional Intervals)...")
    
    # We will use OptionalIntervalVars for students, rooms, and panels to enforce NoOverlap
    # For each shortlist (interview opportunity):
    # We create a presence boolean variable: is_scheduled
    
    student_intervals = {s['student_id']: [] for s in students}
    room_intervals = {r['room_id']: [] for r in rooms}
    panel_intervals = {p['panel_id']: [] for p in panels}
    
    shortlist_assignments = {} # sl_idx -> (is_scheduled, start_var, end_var, room_vars_dict, panel_vars_dict)
    
    for idx, sl in enumerate(shortlists):
        s_id = sl['student_id']
        c_id = sl['company_id']
        comp = company_dict[c_id]
        
        duration_blocks = comp['interview_duration'] // 30
        if duration_blocks < 1: duration_blocks = 1
        
        c_panels = panels_by_company.get(c_id, [])
        if not c_panels:
            continue
            
        # Main presence variable for this interview
        is_scheduled = model.NewBoolVar(f"sched_{idx}_{s_id}_{c_id}")
        start_var = model.NewIntVar(0, TOTAL_SLOTS - duration_blocks, f"start_{idx}")
        end_var = model.NewIntVar(0, TOTAL_SLOTS, f"end_{idx}")
        
        model.Add(end_var == start_var + duration_blocks)
        
        # Student interval
        student_interval = model.NewOptionalIntervalVar(
            start_var, duration_blocks, end_var, is_scheduled, f"s_int_{idx}"
        )
        student_intervals[s_id].append(student_interval)
        
        # Room alternatives
        room_presences = []
        room_vars_dict = {}
        for r in rooms:
            r_id = r['room_id']
            r_pres = model.NewBoolVar(f"r_pres_{idx}_{r_id}")
            r_int = model.NewOptionalIntervalVar(start_var, duration_blocks, end_var, r_pres, f"r_int_{idx}_{r_id}")
            room_intervals[r_id].append(r_int)
            room_presences.append(r_pres)
            room_vars_dict[r_id] = r_pres
            
        # Panel alternatives
        panel_presences = []
        panel_vars_dict = {}
        for p_id in c_panels:
            p_pres = model.NewBoolVar(f"p_pres_{idx}_{p_id}")
            p_int = model.NewOptionalIntervalVar(start_var, duration_blocks, end_var, p_pres, f"p_int_{idx}_{p_id}")
            panel_intervals[p_id].append(p_int)
            panel_presences.append(p_pres)
            panel_vars_dict[p_id] = p_pres
            
        # Link main presence with alternative presences
        model.AddExactlyOne(room_presences).OnlyEnforceIf(is_scheduled)
        for r_pres in room_presences:
            model.AddImplication(r_pres, is_scheduled)
            
        model.AddExactlyOne(panel_presences).OnlyEnforceIf(is_scheduled)
        for p_pres in panel_presences:
            model.AddImplication(p_pres, is_scheduled)
            
        shortlist_assignments[idx] = (is_scheduled, start_var, room_vars_dict, panel_vars_dict, s_id, c_id)

    print("Adding NoOverlap constraints...")
    for s_id, intervals in student_intervals.items():
        if intervals: model.AddNoOverlap(intervals)
        
    for r_id, intervals in room_intervals.items():
        if intervals: model.AddNoOverlap(intervals)
        
    for p_id, intervals in panel_intervals.items():
        if intervals: model.AddNoOverlap(intervals)

    print("Adding objective function...")
    # Maximize scheduled interviews, weight by priority
    objective_terms = []
    for idx, data in shortlist_assignments.items():
        is_scheduled = data[0]
        c_id = data[5]
        priority = company_dict[c_id]['priority']
        weight = 10 if priority == 'HIGH' else (5 if priority == 'MEDIUM' else 2)
        objective_terms.append(is_scheduled * weight)
        
    model.Maximize(sum(objective_terms))

    print("Solving... (Limited to 60 seconds for fast replanning)")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    # Enable logging to see progress
    solver.parameters.log_search_progress = True
    
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"Solution found! Status: {solver.StatusName(status)}")
        print(f"Objective Value: {solver.ObjectiveValue()}")
        save_schedule(solver, shortlist_assignments, company_dict)
    elif status == cp_model.UNKNOWN:
        print("Solver time limit reached before finding a solution. Try running longer.")
    else:
        print("No feasible solution found.")

def save_schedule(solver, shortlist_assignments, company_dict):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("DELETE FROM interviews")
    
    interviews = []
    for idx, data in shortlist_assignments.items():
        is_scheduled, start_var, room_vars_dict, panel_vars_dict, s_id, c_id = data
        
        if solver.Value(is_scheduled):
            slot = solver.Value(start_var)
            
            # Find chosen room
            chosen_r_id = next(r_id for r_id, r_pres in room_vars_dict.items() if solver.Value(r_pres))
            # Find chosen panel
            chosen_p_id = next(p_id for p_id, p_pres in panel_vars_dict.items() if solver.Value(p_pres))
            
            day_idx = slot // SLOTS_PER_DAY
            slot_idx = slot % SLOTS_PER_DAY
            day_name = DAYS[day_idx]
            
            start_hour = 9 + (slot_idx // 2)
            start_min = 30 * (slot_idx % 2)
            start_time = f"{start_hour:02d}:{start_min:02d}"
            
            duration = company_dict[c_id]['interview_duration']
            duration_blocks = duration // 30
            
            end_slot = slot_idx + duration_blocks
            end_hour = 9 + (end_slot // 2)
            end_min = 30 * (end_slot % 2)
            end_time = f"{end_hour:02d}:{end_min:02d}"
            
            interview_id = f"INT-{uuid.uuid4().hex[:8]}"
            
            interviews.append((
                interview_id, s_id, c_id, chosen_p_id, chosen_r_id, day_name, start_time, end_time, 'SCHEDULED'
            ))
            
    cur.executemany(
        "INSERT INTO interviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
        interviews
    )
    conn.commit()
    conn.close()
    
    print(f"Successfully saved {len(interviews)} interviews to the database!")

if __name__ == '__main__':
    # Ensure stdout flushes immediately
    sys.stdout.reconfigure(line_buffering=True)
    generate_schedule()
