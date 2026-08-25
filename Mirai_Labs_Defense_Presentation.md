# Mirai Labs - Placement Week Scheduler Defense

**Candidate:** Prajwal V
**Role:** Software Developer Intern
**Project:** Placement Administration OS

---

## Slide 1: The Whiteboard Problem (Introduction)

**Speaker Notes:**
"Hello everyone, thank you for having me. When I looked at the placement week scenario—800 students, 35 companies, overlapping shortlists, and constant real-time chaos—it became clear why a physical whiteboard collapses. A whiteboard has no memory, no mathematical guarantees, and no ability to predict the blast radius of a single delay. 

My goal was to build a system that guarantees mathematical correctness using a CP-SAT solver, while giving the coordinator a deterministic, zero-confusion dashboard to manage the chaos on the day."

---

## Slide 2: Data Generation & Realism

**Speaker Notes:**
"To ensure the system works under pressure, I built a highly realistic data generator. 
- It simulates the 'Day-1 Mass Recruiter' phenomenon where a few companies shortlist hundreds of students.
- It models top-tier students appearing on multiple overlapping lists.
- Companies have strict CGPA cutoffs, varying panel counts, and different interview durations.
This ensures the solver isn't just solving a toy problem, but a dense, highly constrained real-world scenario."

---

## Slide 3: The Engine - Feasibility vs. Infeasibility

**Speaker Notes:**
"For the core engine, I used Google OR-Tools (CP-SAT). 
The strict rule I imposed is: **Hard constraints never bend.** No student can be in two places at once, and no room can hold two interviews. 

If the system faces an impossible schedule, it does not fail silently, nor does it hallucinate a broken schedule. Instead, it schedules the maximum possible interviews based on company priority, and clearly outputs the unscheduled interviews for the coordinator to manually review. The system is an assistant, not an override."

---

## Slide 4: The Heart of the System - Replanning under Disruption

**Speaker Notes:**
"During placement week, a company arriving 2 hours late shouldn't cause 200 unrelated interviews to be reshuffled. 
To handle replanning, I implemented an Impact Analyzer and a localized Solver. 

When a disruption happens, the system:
1. Freezes all unaffected interviews.
2. Identifies the exact 'blast radius' of the incident.
3. Reschedules only the affected interviews.

This answers the critical question: How much reshuffling is acceptable? The answer is: Only the mathematical minimum required to maintain feasibility. Minimizing 'churn' is our primary objective function during a replan."

---

## Slide 5: Live Defense Scenario Walkthrough

**The Scenario:** *“The biggest Day-1 recruiter is 3 hours late, one of its panels dropped, and 15 students just withdrew.”*

**How to execute this in the dashboard:**
"Because incidents in real life are reported sequentially (a coordinator gets a call about a delay, then an email about a dropout), the dashboard is designed to handle compounding sequential disruptions gracefully. 

1. **Step 1:** Select `COMPANY_DELAY`, select the Day-1 company, set delay to 180 minutes. Hit Replan.
2. **Step 2:** Select `PANEL_DROPOUT`, select the specific panel belonging to that company. Hit Replan.
3. **Step 3:** Select `STUDENT_WITHDRAWAL` for the students. Hit Replan.

The system will instantly calculate the cascading impact and output a color-coded diff showing exactly who moved rooms, who moved times, and who couldn't be scheduled."

---

## Slide 6: Conclusion

**Speaker Notes:**
"Ultimately, this system transforms the placement coordinator from a reactive firefighter into a proactive manager. Thank you, and I am ready to jump into the Live Dashboard demonstration."
