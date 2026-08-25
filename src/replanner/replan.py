import sys
from ortools.sat.python import cp_model
from src.database.db import get_db_connection
from src.scheduler.validator import time_to_minutes
from src.scheduler.solver import DAYS, SLOTS_PER_DAY, TOTAL_SLOTS
import uuid

def perform_replan(impacted_interviews):
    """
    Replans ONLY the impacted interviews, treating the rest of the schedule as frozen constraints.
    """
    if not impacted_interviews:
        print("No interviews to replan.")
        return []
        
    conn = get_db_connection()
    # Get all active resources
    active_rooms = [dict(row) for row in conn.execute("SELECT * FROM rooms WHERE status='ACTIVE'").fetchall()]
    active_panels = [dict(row) for row in conn.execute("SELECT * FROM panels WHERE status='ACTIVE'").fetchall()]
    companies = {c['company_id']: dict(c) for c in conn.execute("SELECT * FROM companies").fetchall()}
    
    # Get frozen interviews (not impacted)
    impacted_ids = set(i['interview_id'] for i in impacted_interviews)
    all_scheduled = [dict(row) for row in conn.execute("SELECT * FROM interviews WHERE status='SCHEDULED'").fetchall()]
    frozen_interviews = [i for i in all_scheduled if i['interview_id'] not in impacted_ids]
    conn.close()

    model = cp_model.CpModel()
    
    # 1. Build fixed intervals for frozen interviews
    student_intervals = {}
    room_intervals = {}
    panel_intervals = {}
    
    def get_slot_from_time(day_name, start_time):
        day_idx = DAYS.index(day_name)
        mins = time_to_minutes(start_time)
        slot_in_day = (mins - time_to_minutes("09:00")) // 30
        return day_idx * SLOTS_PER_DAY + slot_in_day

    for inv in frozen_interviews:
        slot = get_slot_from_time(inv['date'], inv['start_time'])
        duration_blocks = companies[inv['company_id']]['interview_duration'] // 30
        if duration_blocks < 1: duration_blocks = 1
        
        interval = model.NewFixedSizeIntervalVar(slot, duration_blocks, f"frozen_{inv['interview_id']}")
        
        student_intervals.setdefault(inv['student_id'], []).append(interval)
        room_intervals.setdefault(inv['room_id'], []).append(interval)
        panel_intervals.setdefault(inv['panel_id'], []).append(interval)

    # 2. Build variables for impacted interviews
    impacted_assignments = {}
    
    panels_by_company = {}
    for p in active_panels:
        panels_by_company.setdefault(p['company_id'], []).append(p['panel_id'])
        
    print(f"Building replan model for {len(impacted_interviews)} interviews...")
    
    for idx, inv in enumerate(impacted_interviews):
        s_id = inv['student_id']
        c_id = inv['company_id']
        comp = companies[c_id]
        
        duration_blocks = comp['interview_duration'] // 30
        if duration_blocks < 1: duration_blocks = 1
        
        c_panels = panels_by_company.get(c_id, [])
        
        is_scheduled = model.NewBoolVar(f"rsched_{idx}")
        start_var = model.NewIntVar(0, TOTAL_SLOTS - duration_blocks, f"rstart_{idx}")
        end_var = model.NewIntVar(0, TOTAL_SLOTS, f"rend_{idx}")
        model.Add(end_var == start_var + duration_blocks)
        
        student_interval = model.NewOptionalIntervalVar(start_var, duration_blocks, end_var, is_scheduled, f"rs_int_{idx}")
        student_intervals.setdefault(s_id, []).append(student_interval)
        
        room_presences = []
        room_vars_dict = {}
        for r in active_rooms:
            r_id = r['room_id']
            r_pres = model.NewBoolVar(f"rr_pres_{idx}_{r_id}")
            r_int = model.NewOptionalIntervalVar(start_var, duration_blocks, end_var, r_pres, f"rr_int_{idx}_{r_id}")
            room_intervals.setdefault(r_id, []).append(r_int)
            room_presences.append(r_pres)
            room_vars_dict[r_id] = r_pres
            
        panel_presences = []
        panel_vars_dict = {}
        for p_id in c_panels:
            p_pres = model.NewBoolVar(f"rp_pres_{idx}_{p_id}")
            p_int = model.NewOptionalIntervalVar(start_var, duration_blocks, end_var, p_pres, f"rp_int_{idx}_{p_id}")
            panel_intervals.setdefault(p_id, []).append(p_int)
            panel_presences.append(p_pres)
            panel_vars_dict[p_id] = p_pres
            
        # Tie to main presence
        if room_presences and panel_presences:
            model.AddExactlyOne(room_presences).OnlyEnforceIf(is_scheduled)
            for r_pres in room_presences: model.AddImplication(r_pres, is_scheduled)
            model.AddExactlyOne(panel_presences).OnlyEnforceIf(is_scheduled)
            for p_pres in panel_presences: model.AddImplication(p_pres, is_scheduled)
        else:
            model.Add(is_scheduled == 0) # Impossible to schedule
            
        # Bonus for keeping the same timeslot to minimize churn
        same_time = model.NewBoolVar(f"same_time_{idx}")
        orig_slot = get_slot_from_time(inv['date'], inv['start_time'])
        model.Add(start_var == orig_slot).OnlyEnforceIf(same_time)
        model.Add(start_var != orig_slot).OnlyEnforceIf(same_time.Not())
            
        impacted_assignments[idx] = (is_scheduled, start_var, room_vars_dict, panel_vars_dict, inv, same_time)

    # 3. Add NoOverlap
    for intervals in student_intervals.values():
        if len(intervals) > 1: model.AddNoOverlap(intervals)
    for intervals in room_intervals.values():
        if len(intervals) > 1: model.AddNoOverlap(intervals)
    for intervals in panel_intervals.values():
        if len(intervals) > 1: model.AddNoOverlap(intervals)

    # 4. Maximize scheduled AND minimize churn (bonus for same time)
    objective_terms = []
    for idx, data in impacted_assignments.items():
        is_scheduled = data[0]
        same_time = data[5]
        # Huge bonus for scheduling at all, smaller bonus for keeping original slot
        objective_terms.append(is_scheduled * 100)
        objective_terms.append(same_time * 10)
        
    model.Maximize(sum(objective_terms))

    print("Solving replan... (Limit: 10s)")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)

    replanned = []
    unscheduled = []

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"Replan Solution found! Status: {solver.StatusName(status)}")
        
        # Save diff
        conn = get_db_connection()
        cur = conn.cursor()
        
        for idx, data in impacted_assignments.items():
            is_scheduled, start_var, room_vars_dict, panel_vars_dict, orig_inv, _ = data
            
            if solver.Value(is_scheduled):
                slot = solver.Value(start_var)
                chosen_r_id = next(r_id for r_id, r_pres in room_vars_dict.items() if solver.Value(r_pres))
                chosen_p_id = next(p_id for p_id, p_pres in panel_vars_dict.items() if solver.Value(p_pres))
                
                day_idx = slot // SLOTS_PER_DAY
                slot_idx = slot % SLOTS_PER_DAY
                
                start_hour = 9 + (slot_idx // 2)
                start_min = 30 * (slot_idx % 2)
                start_time = f"{start_hour:02d}:{start_min:02d}"
                
                duration = companies[orig_inv['company_id']]['interview_duration']
                end_slot = slot_idx + (duration // 30)
                end_hour = 9 + (end_slot // 2)
                end_min = 30 * (end_slot % 2)
                end_time = f"{end_hour:02d}:{end_min:02d}"
                
                # Update DB
                cur.execute('''
                    UPDATE interviews 
                    SET room_id=?, panel_id=?, date=?, start_time=?, end_time=?
                    WHERE interview_id=?
                ''', (chosen_r_id, chosen_p_id, DAYS[day_idx], start_time, end_time, orig_inv['interview_id']))
                
                replanned.append({
                    'interview_id': orig_inv['interview_id'],
                    'student_id': orig_inv['student_id'],
                    'company_id': orig_inv['company_id'],
                    'old_room': orig_inv['room_id'],
                    'new_room': chosen_r_id,
                    'old_time': orig_inv['start_time'],
                    'new_time': start_time
                })
            else:
                cur.execute("UPDATE interviews SET status='CANCELLED' WHERE interview_id=?", (orig_inv['interview_id'],))
                unscheduled.append(orig_inv['interview_id'])
                
        conn.commit()
        conn.close()
    else:
        print("No feasible replan possible!")
        
    print(f"Replanned: {len(replanned)} | Cancelled: {len(unscheduled)}")
    return replanned, unscheduled
