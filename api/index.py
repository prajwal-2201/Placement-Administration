import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Fix path to import src modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
global_import_error = None
try:
    from src.database.db import get_db_connection
    from src.replanner.disruption import apply_disruption
    from src.replanner.impact import calculate_impact
    from src.replanner.replan import perform_replan
    from src.scheduler.validator import validate_schedule
except Exception as e:
    import traceback
    global_import_error = traceback.format_exc()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for local testing
public_path = os.path.join(os.path.dirname(__file__), '..', 'public')
if os.path.exists(public_path):
    app.mount("/public", StaticFiles(directory=public_path), name="public")

@app.get("/")
async def root():
    return FileResponse(os.path.join(public_path, 'index.html'))

@app.post("/api/reset")
def reset_database():
    from src.database.db import reset_db
    reset_db()
    return {"status": "success", "message": "Database reset to initial state"}

class DisruptionPayload(BaseModel):
    type: str
    target_id: str
    delay_minutes: int = 0

@app.get("/api/dashboard")
def get_dashboard_data():
    if global_import_error:
        return {"error": "Import Failed", "traceback": global_import_error}
    conn = get_db_connection()
    metrics = {
        'completed': conn.execute("SELECT COUNT(*) FROM interviews WHERE status='COMPLETED'").fetchone()[0],
        'upcoming': conn.execute("SELECT COUNT(*) FROM interviews WHERE status='SCHEDULED'").fetchone()[0],
        'rooms': conn.execute("SELECT COUNT(DISTINCT room_id) FROM interviews WHERE status='SCHEDULED'").fetchone()[0],
        'panels': conn.execute("SELECT COUNT(DISTINCT panel_id) FROM interviews WHERE status='SCHEDULED'").fetchone()[0],
    }
    
    rows = conn.execute("""
        SELECT interview_id as ID, student_id as Student, company_id as Company, 
               room_id as Room, panel_id as Panel, date as Date, 
               start_time as Start, end_time as End, status as Status
        FROM interviews ORDER BY date, start_time
    """).fetchall()
    
    schedule = [dict(row) for row in rows]
    
    entities = {
        'rooms': [r[0] for r in conn.execute("SELECT room_id FROM rooms WHERE status='ACTIVE'").fetchall()],
        'panels': [r[0] for r in conn.execute("SELECT panel_id FROM panels WHERE status='ACTIVE'").fetchall()],
        'companies': [r[0] for r in conn.execute("SELECT company_id FROM companies").fetchall()],
        'students': [r[0] for r in conn.execute("SELECT student_id FROM students WHERE status='ACTIVE'").fetchall()]
    }
    conn.close()
    
    return {
        "metrics": metrics,
        "schedule": schedule,
        "entities": entities
    }

@app.get("/api/validate")
def validate_system():
    res = validate_schedule()
    return res

@app.post("/api/replan")
def trigger_replan(payload: DisruptionPayload):
    details = {}
    if payload.type == "COMPANY_DELAY":
        details = {"delay_minutes": payload.delay_minutes}
        
    try:
        d_id = apply_disruption(payload.type, payload.target_id, details)
        impacted = calculate_impact(d_id)
        
        unique_impacted = {i['interview_id']: i for i in impacted}.values()
        unique_impacted = list(unique_impacted)
        
        if len(unique_impacted) == 0:
            return {"impacted_count": 0, "replanned": [], "unscheduled": [], "message": "No impact", "retained_count": 0}
            
        replanned, unscheduled = perform_replan(unique_impacted)
        val_res = validate_schedule()
        
        if not val_res["is_valid"]:
            raise HTTPException(status_code=500, detail="Validation Error: The generated schedule does not meet constraints.")
            
        retained = sum(1 for r in replanned if r['old_time'] == r['new_time'])
            
        return {
            "impacted_count": len(unique_impacted),
            "replanned": replanned,
            "unscheduled": [u['interview_id'] for u in unscheduled],
            "retained_count": retained
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Request
@app.api_route("/{path:path}", methods=["GET", "POST"])
async def catch_all(request: Request, path: str):
    return {"caught_path": path, "url": str(request.url)}
