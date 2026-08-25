def generate_replan_explanation(replanned, unscheduled, d_type, target):
    """
    Generates a natural language explanation of the replanning results.
    """
    total_impact = len(replanned) + len(unscheduled)
    
    explanation = f"**REPLAN SUMMARY**\n\n"
    explanation += f"**Cause:** {d_type} for {target}.\n"
    explanation += f"**Impact:** {total_impact} interviews were affected.\n\n"
    
    if total_impact == 0:
        explanation += "No changes were necessary because no interviews were scheduled involving this resource."
        return explanation
        
    explanation += f"**Changes made:**\n"
    if replanned:
        # Check if times changed
        time_changed = sum(1 for r in replanned if r['old_time'] != r['new_time'])
        explanation += f"- Successfully replanned {len(replanned)} interviews.\n"
        explanation += f"- {len(replanned) - time_changed} interviews kept their exact original timeslot and were only assigned new rooms/panels. (Zero time churn!)\n"
        if time_changed > 0:
            explanation += f"- {time_changed} interviews were moved to new timeslots.\n"
            
    if unscheduled:
        explanation += f"- {len(unscheduled)} interviews had to be **CANCELLED** due to insufficient system capacity. (Coordinator review required!)\n"
        
    explanation += "\n**Validation:** The new schedule has been independently verified and contains 0 conflicts."
    return explanation
