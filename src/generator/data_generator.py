import sqlite3
import random
import json
import os
import string
from src.database.db import get_db_connection, init_db

# Constants
NUM_STUDENTS = 800
NUM_COMPANIES = 35
NUM_ROOMS = 20

BRANCHES = ['CSE', 'ISE', 'ECE', 'MECH', 'CIVIL']

def generate_cgpa():
    # Realistic CGPA distribution
    rand = random.random()
    if rand < 0.20: return round(random.uniform(6.0, 6.5), 2)
    elif rand < 0.50: return round(random.uniform(6.5, 7.5), 2)
    elif rand < 0.80: return round(random.uniform(7.5, 8.5), 2)
    elif rand < 0.95: return round(random.uniform(8.5, 9.2), 2)
    else: return round(random.uniform(9.2, 10.0), 2)

def generate_students():
    students = []
    for i in range(1, NUM_STUDENTS + 1):
        students.append({
            'student_id': f"S{i:04d}",
            'name': f"Student {i}",
            'branch': random.choice(BRANCHES),
            'cgpa': generate_cgpa(),
            'graduation_year': 2027,
            'status': 'ACTIVE'
        })
    return students

def generate_companies():
    companies = []
    # 5 Mass Recruiters, 10 Premium, 10 Product, 10 Niche
    types = ['MASS'] * 5 + ['PREMIUM'] * 10 + ['PRODUCT'] * 10 + ['NICHE'] * 10
    random.shuffle(types)

    for i in range(1, NUM_COMPANIES + 1):
        c_type = types[i-1]
        if c_type == 'MASS':
            priority = 'HIGH'
            cutoff = random.uniform(6.0, 6.5)
            duration = 30
            panels = random.randint(5, 8)
            pref_days = ['Day 1', 'Day 2']
            branches = BRANCHES
        elif c_type == 'PREMIUM':
            priority = 'MEDIUM'
            cutoff = random.uniform(7.0, 7.5)
            duration = 45
            panels = random.randint(3, 5)
            pref_days = ['Day 2', 'Day 3']
            branches = ['CSE', 'ISE', 'ECE']
        elif c_type == 'PRODUCT':
            priority = 'HIGH'
            cutoff = random.uniform(7.5, 8.5)
            duration = 60
            panels = random.randint(2, 4)
            pref_days = ['Day 1', 'Day 2']
            branches = ['CSE', 'ISE']
        else: # NICHE
            priority = 'LOW'
            cutoff = random.uniform(6.5, 7.5)
            duration = 45
            panels = random.randint(1, 2)
            pref_days = ['Day 3', 'Day 4']
            branches = [random.choice(BRANCHES)]

        companies.append({
            'company_id': f"C{i:03d}",
            'name': f"{c_type.title()} Corp {string.ascii_uppercase[i % 26]}",
            'priority': priority,
            'cgpa_cutoff': round(cutoff, 2),
            'interview_duration': duration,
            'number_of_panels': panels,
            'preferred_days': json.dumps(pref_days),
            'arrival_time': '09:00',
            'departure_time': '18:00',
            'branch_preferences': json.dumps(branches)
        })
    return companies

def generate_shortlists(students, companies):
    shortlists = []
    for c in companies:
        c_branches = json.loads(c['branch_preferences'])
        for s in students:
            if s['cgpa'] >= c['cgpa_cutoff'] and s['branch'] in c_branches:
                # Add some randomness so not EVERY eligible student applies
                if random.random() < 0.8:
                    shortlists.append({
                        'student_id': s['student_id'],
                        'company_id': c['company_id']
                    })
    return shortlists

def generate_rooms():
    rooms = []
    for i in range(1, NUM_ROOMS + 1):
        capacity = 50 if i <= 3 else (30 if i <= 10 else 20)
        rooms.append({
            'room_id': f"R{i:02d}",
            'building': 'Main Block',
            'capacity': capacity,
            'available_days': json.dumps(['Day 1', 'Day 2', 'Day 3', 'Day 4']),
            'available_times': json.dumps(['09:00-18:00']),
            'status': 'ACTIVE'
        })
    return rooms

def generate_panels(companies):
    panels = []
    for c in companies:
        for p in range(1, c['number_of_panels'] + 1):
            panels.append({
                'panel_id': f"P-{c['company_id']}-{p:02d}",
                'company_id': c['company_id'],
                'members': random.randint(2, 4),
                'available_days': c['preferred_days'],
                'available_times': json.dumps(['09:00-18:00']),
                'status': 'ACTIVE'
            })
    return panels

def generate_all_data():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()

    print("Generating students...")
    students = generate_students()
    cur.executemany("INSERT INTO students VALUES (:student_id, :name, :branch, :cgpa, :graduation_year, :status)", students)

    print("Generating companies...")
    companies = generate_companies()
    cur.executemany("INSERT INTO companies VALUES (:company_id, :name, :priority, :cgpa_cutoff, :interview_duration, :number_of_panels, :preferred_days, :arrival_time, :departure_time, :branch_preferences)", companies)

    print("Generating shortlists...")
    shortlists = generate_shortlists(students, companies)
    cur.executemany("INSERT INTO shortlists VALUES (:student_id, :company_id)", shortlists)

    print("Generating rooms...")
    rooms = generate_rooms()
    cur.executemany("INSERT INTO rooms VALUES (:room_id, :building, :capacity, :available_days, :available_times, :status)", rooms)

    print("Generating panels...")
    panels = generate_panels(companies)
    cur.executemany("INSERT INTO panels VALUES (:panel_id, :company_id, :members, :available_days, :available_times, :status)", panels)

    conn.commit()
    conn.close()
    
    print(f"Generation complete!")
    print(f"Students: {len(students)}")
    print(f"Companies: {len(companies)}")
    print(f"Shortlists: {len(shortlists)}")
    print(f"Rooms: {len(rooms)}")
    print(f"Panels: {len(panels)}")

if __name__ == '__main__':
    generate_all_data()
