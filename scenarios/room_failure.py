import sys
import os

# Ensure we can import from src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.replanner.disruption import apply_disruption
from src.replanner.impact import calculate_impact
from src.replanner.replan import perform_replan
from src.scheduler.validator import validate_schedule

def simulate_room_failure():
    print("=== SCENARIO: ROOM R12 UNAVAILABLE ===")
    
    # 1. Apply Disruption
    d_id = apply_disruption('ROOM_UNAVAILABLE', 'R12', {})
    
    # 2. Impact Analysis
    impacted = calculate_impact(d_id)
    
    if not impacted:
        print("No interviews were affected. No replan needed.")
        return
        
    # 3. Replanner
    print("\nStarting minimal-churn replan...")
    replanned, unscheduled = perform_replan(impacted)
    
    print(f"\n--- DIFF SUMMARY ---")
    for r in replanned:
        print(f"[{r['interview_id']}] Moved from {r['old_room']} @ {r['old_time']} -> {r['new_room']} @ {r['new_time']}")
        
    for u in unscheduled:
        print(f"[{u}] ❌ CANCELLED (No capacity left)")
        
    # 4. Final Validation
    print("\nValidating new schedule...")
    validate_schedule()

if __name__ == '__main__':
    simulate_room_failure()
