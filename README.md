# University Placement Administration System

An advanced constraint-optimized scheduling and dynamic replanning system built for complex university placement drives.

## 📖 The Story So Far...

**Day 3 of Placement Week:** Over the last two days, **268 interviews** have successfully taken place across 17 rooms and 95 interview panels. However, reality rarely sticks to the plan. Panels drop out, students withdraw, companies run late, and rooms become unavailable. 

When a critical incident occurs (like a room losing power), the naive approach is to cancel all affected interviews or manually shuffle them, causing cascading chaos. This system takes a different approach: it freezes the unaffected interviews and uses a powerful constraint-optimization engine to find the path of least resistance, minimizing churn while mathematically guaranteeing zero overlapping resource conflicts.

## 🚀 Key Features

1. **CP-SAT Scheduling Engine:** Uses Google OR-Tools to compute optimal schedules, maximizing company priority while strictly enforcing hardware/resource constraints (no double-booked rooms, panels, or students).
2. **Dynamic Replanner & Impact Analysis:** Handles real-world disruptions (Room down, Panel dropout, Student withdrawal, Company late) by automatically calculating the blast radius and efficiently rescheduling only the affected interviews.
3. **Independent Constraint Validator:** A standalone verification layer that mathematically guarantees no invalid schedule is ever persisted.
4. **Realistic Data Pipeline:** Bootstraps hundreds of students, companies (Mass, Premium, Product, Niche), rooms, and panels with realistic distributions.
5. **Interactive Dashboard:** A clean, professional, enterprise-grade Streamlit application for administrators to monitor the schedule and report live incidents via a deterministic interface.

## 🏗️ Architecture & Approach

This system is broken down into modular, decoupled components to ensure scalability and reliability:

- **`src/generator/`**: Synthesizes the initial state of the world, generating a SQLite database populated with complex relationships and the initial constraint-solved schedule.
- **`src/scheduler/`**: Contains the core OR-Tools CP-SAT logic. It converts business rules into mathematical constraints.
- **`src/replanner/`**: The reactive engine. When a disruption is logged, it identifies all downstream impacts and runs a localized CP-SAT optimization to patch the schedule with minimal disruption to the wider system.
- **`dashboard/`**: The frontend layer. Built with Streamlit, it provides a clean, incident-management UI for administrators.

## 💻 Setup & Installation

**Prerequisites:** Python 3.10+

1. **Clone the repository:**
   ```bash
   git clone https://github.com/prajwal-2201/Placement-Administration.git
   cd Placement-Administration
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the Database & Generate Initial Schedule:**
   ```bash
   # Generates the baseline data and runs the initial CP-SAT solver
   python src/generator/data_generator.py
   python src/scheduler/solver.py
   ```

5. **Run the Independent Validator (Optional but recommended):**
   ```bash
   python src/scheduler/validator.py
   ```

6. **Launch the Dashboard:**
   ```bash
   streamlit run dashboard/app.py
   ```
   Navigate to `http://localhost:8501` to view the application.

## 🧪 Testing Disruptions

Once the dashboard is running, navigate to the **Incident Management** tab:
1. Select **Incident Type** (e.g., `ROOM_UNAVAILABLE`).
2. Select a target entity (e.g., Room `R01`).
3. Click **Analyze Impact & Replan**. 
4. The system will calculate the affected interviews (e.g., 27 interviews) and output a color-coded diff showing the exact room and time changes made to preserve the schedule.
