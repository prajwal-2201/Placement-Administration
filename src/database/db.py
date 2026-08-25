import sqlite3
import os
import shutil

# Master DB (read-only in Vercel)
MASTER_DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'scheduler.db')

# Active DB (writable in Vercel's /tmp)
# On Windows/local, we can just use a local tmp dir or the same.
if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/scheduler.db'
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'scheduler_active.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT,
    branch TEXT,
    cgpa REAL,
    graduation_year INTEGER,
    status TEXT
);

CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    name TEXT,
    priority TEXT,
    cgpa_cutoff REAL,
    interview_duration INTEGER,
    number_of_panels INTEGER,
    preferred_days TEXT,
    arrival_time TEXT,
    departure_time TEXT,
    branch_preferences TEXT
);

CREATE TABLE IF NOT EXISTS shortlists (
    student_id TEXT,
    company_id TEXT,
    PRIMARY KEY (student_id, company_id),
    FOREIGN KEY(student_id) REFERENCES students(student_id),
    FOREIGN KEY(company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS rooms (
    room_id TEXT PRIMARY KEY,
    building TEXT,
    capacity INTEGER,
    available_days TEXT,
    available_times TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS panels (
    panel_id TEXT PRIMARY KEY,
    company_id TEXT,
    members INTEGER,
    available_days TEXT,
    available_times TEXT,
    status TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS interviews (
    interview_id TEXT PRIMARY KEY,
    student_id TEXT,
    company_id TEXT,
    panel_id TEXT,
    room_id TEXT,
    date TEXT,
    start_time TEXT,
    end_time TEXT,
    status TEXT,
    FOREIGN KEY(student_id) REFERENCES students(student_id),
    FOREIGN KEY(company_id) REFERENCES companies(company_id),
    FOREIGN KEY(panel_id) REFERENCES panels(panel_id),
    FOREIGN KEY(room_id) REFERENCES rooms(room_id)
);

CREATE TABLE IF NOT EXISTS disruptions (
    disruption_id TEXT PRIMARY KEY,
    type TEXT,
    target_id TEXT,
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def reset_db():
    """Copies the master database to the active database to reset all changes."""
    if os.path.exists(MASTER_DB_PATH):
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except:
                pass
        shutil.copy2(MASTER_DB_PATH, DB_PATH)
        print(f"Database reset from {MASTER_DB_PATH} to {DB_PATH}")
    else:
        print(f"Master DB not found at {MASTER_DB_PATH}, cannot reset.")

def init_db():
    os.makedirs(os.path.dirname(MASTER_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(MASTER_DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    reset_db()

def get_db_connection():
    if not os.path.exists(DB_PATH):
        reset_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    init_db()
