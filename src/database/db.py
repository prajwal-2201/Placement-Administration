import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'scheduler.db')

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

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    init_db()
