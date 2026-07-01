"""
VTU Result Scraper -- FastAPI Backend
======================================
Run with: python -m uvicorn api.main:app --reload --port 8000

Frontend: http://localhost:8000
API Docs: http://localhost:8000/docs
"""
import os
import threading
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

import urllib3
urllib3.disable_warnings()

from src.batch_runner import generate_usns, run_batch_and_export
from src.database import (
    get_all_results, get_result_by_usn, get_results_count
)
from src.exporter import export_to_excel
from src.calculator import calculate_sgpa, calculate_cgpa, get_credits
from src.config import EXPORTS_DIR

# Resolve paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# -- FastAPI App --
app = FastAPI(
    title="VTU Result Scraper API",
    description="Automated VTU exam result scraper with CAPTCHA bypass, revaluation comparison, and Excel export.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# -- In-memory job tracking --
jobs = {}


# -- Request/Response Models --

class ScrapeRequest(BaseModel):
    url: str
    college_code: str
    year: str
    branch: str
    start_roll: int
    end_roll: int
    is_reval: bool = False
    delay: float = 0.5
    max_retries: int = 15


class ScrapeResponse(BaseModel):
    job_id: str
    message: str
    total_students: int


# -- Frontend Route --

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """Serve the main frontend page."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend not found. Place index.html in /static/</h1>")

@app.get("/admin", response_class=HTMLResponse)
def serve_admin():
    """Serve the admin frontend page."""
    admin_path = os.path.join(STATIC_DIR, "admin", "index.html")
    if os.path.exists(admin_path):
        with open(admin_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Admin Frontend not found.</h1>")

# -- API Routes --

@app.post("/api/scrape", response_model=ScrapeResponse)
def start_scrape(req: ScrapeRequest):
    """Start a batch scraping job."""
    
    usns = generate_usns(req.college_code, req.year, req.branch, req.start_roll, req.end_roll)
    
    if not usns:
        raise HTTPException(status_code=400, detail="Invalid roll range: no USNs generated.")
    
    job_id = str(uuid.uuid4())[:8]
    
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "total": len(usns),
        "current_usn": None,
        "current_status": None,
        "started_at": datetime.now().isoformat(),
        "summary": None,
        "excel_path": None,
        "results_log": [],
        "usns": usns,  # Store for later export reference
    }
    
    def progress_callback(current, total, usn, status):
        jobs[job_id]["progress"] = current
        jobs[job_id]["current_usn"] = usn
        jobs[job_id]["current_status"] = status
        jobs[job_id]["results_log"].append({"usn": usn, "status": status})
    
    def run_in_background():
        try:
            summary, excel_path = run_batch_and_export(
                url=req.url,
                usns=usns,
                is_reval=req.is_reval,
                delay=req.delay,
                max_retries=req.max_retries,
                progress_callback=progress_callback
            )
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["summary"] = summary
            jobs[job_id]["excel_path"] = excel_path
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["summary"] = {"error": str(e)}
    
    thread = threading.Thread(target=run_in_background, daemon=True)
    thread.start()
    
    return ScrapeResponse(
        job_id=job_id,
        message=f"Scraping started for {len(usns)} students.",
        total_students=len(usns)
    )


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    """Check the progress of a scraping job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "total": job["total"],
        "percentage": round((job["progress"] / job["total"]) * 100, 1) if job["total"] > 0 else 0,
        "current_usn": job.get("current_usn"),
        "current_status": job.get("current_status"),
        "started_at": job.get("started_at"),
        "summary": job.get("summary"),
        "results_log": job.get("results_log", [])[-15:]  # Last 15 entries
    }


@app.get("/api/results/{usn}")
def get_result(usn: str):
    """Get a single student's result by USN."""
    result = get_result_by_usn(usn.upper())
    if not result:
        raise HTTPException(status_code=404, detail=f"No result found for USN: {usn}")
        
    subjects = result.get("subjects", {})
    for code, sub in subjects.items():
        sub["credits"] = get_credits(code)
        
    sems = list(set([s.get("semester", 0) for s in subjects.values()]))
    latest_sem = max(sems) if sems else 0
    result["sgpa"], _ = calculate_sgpa(subjects, target_sem=latest_sem)
    result["cgpa"], _ = calculate_cgpa(subjects)
    
    result["sgpa_map"] = {}
    for sem in sems:
        sem_sgpa, _ = calculate_sgpa(subjects, target_sem=sem)
        result["sgpa_map"][sem] = sem_sgpa
    
    return result


@app.get("/api/results")
def get_all_results_endpoint():
    """Get all student results with computed SGPA and CGPA."""
    results = get_all_results()
    if not results:
        return {"results": []}
    
    for result in results:
        subjects = result.get("subjects", {})
        for code, sub in subjects.items():
            sub["credits"] = get_credits(code)
            
        sems = list(set([s.get("semester", 0) for s in subjects.values()]))
        latest_sem = max(sems) if sems else 0
        result["sgpa"], _ = calculate_sgpa(subjects, target_sem=latest_sem)
        result["cgpa"], _ = calculate_cgpa(subjects)
        
        result["sgpa_map"] = {}
        for sem in sems:
            sem_sgpa, _ = calculate_sgpa(subjects, target_sem=sem)
            result["sgpa_map"][sem] = sem_sgpa
            
    return {"results": results}



@app.get("/api/export")
def export_all(semester: Optional[int] = None):
    """Export all DB results to Excel. Optional semester filter."""
    results = get_all_results()
    if not results:
        raise HTTPException(status_code=404, detail="No results in database to export.")
    
    if semester:
        filtered = []
        for student in results:
            subjects = student.get("subjects", {})
            sem_subjects = {
                code: sub for code, sub in subjects.items()
                if (sub.get("semester") or 0) == semester
            }
            if sem_subjects:
                filtered.append({
                    **student,
                    "subjects": sem_subjects,
                    "grand_total": sum(s.get("total", 0) for s in sem_subjects.values())
                })
        results = filtered
        prefix = f"Sem{semester}_results"
    else:
        # Build prefix from USN range
        usns = sorted([r.get("usn", "") for r in results if r.get("usn")])
        if usns:
            prefix = f"{usns[0]}_to_{usns[-1]}"
        else:
            prefix = "all_results"
    
    if not results:
        raise HTTPException(status_code=404, detail=f"No results found for semester {semester}.")
    
    excel_path = export_to_excel(results, prefix=prefix)
    if not excel_path or not os.path.exists(excel_path):
        raise HTTPException(status_code=500, detail="Failed to generate Excel file.")
    
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(excel_path)
    )


@app.get("/api/export/{job_id}")
def download_export(job_id: str):
    """Download the Excel file generated by a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    
    job = jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job is still {job['status']}.")
    
    excel_path = job.get("excel_path")
    if not excel_path or not os.path.exists(excel_path):
        raise HTTPException(status_code=404, detail="Excel file not found.")
    
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(excel_path)
    )


@app.get("/api/semesters")
def get_semesters():
    """Get list of all semesters available in the database."""
    results = get_all_results()
    sems = set()
    for student in results:
        for code, sub in student.get("subjects", {}).items():
            sem = sub.get("semester") or 0
            if sem > 0:
                sems.add(sem)
    return {"semesters": sorted(sems)}


@app.get("/api/stats")
def get_stats():
    """Get database statistics."""
    count = get_results_count()
    return {
        "total_students": count,
        "active_jobs": sum(1 for j in jobs.values() if j["status"] == "running"),
        "completed_jobs": sum(1 for j in jobs.values() if j["status"] == "completed"),
    }


@app.delete("/api/cleanup")
def cleanup_files():
    """Clean up old export files and temp data."""
    import glob
    
    # Clean exports (keep only latest 3)
    export_files = sorted(
        glob.glob(os.path.join(EXPORTS_DIR, "*.xlsx")),
        key=os.path.getmtime, reverse=True
    )
    removed = 0
    for f in export_files[3:]:
        try:
            os.remove(f)
            removed += 1
        except OSError:
            pass
    
    # Clean temp
    temp_dir = os.path.join(BASE_DIR, "temp")
    if os.path.exists(temp_dir):
        for f in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, f))
                removed += 1
            except OSError:
                pass
    
    # Clean stale jobs (older than completed)
    stale_jobs = [jid for jid, j in jobs.items() if j["status"] in ("completed", "error")]
    for jid in stale_jobs:
        del jobs[jid]
    
    return {
        "files_removed": removed,
        "stale_jobs_cleared": len(stale_jobs),
        "message": f"Cleaned up {removed} files and {len(stale_jobs)} stale jobs."
    }
