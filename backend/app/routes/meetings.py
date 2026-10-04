import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from backend.app.services.pipeline_service import process_meeting_background, OUTPUTS_DIR

router = APIRouter()
UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/uploads"))

@router.post("/process")
async def process_meeting(background_tasks: BackgroundTasks, video: UploadFile = File(...)):
    if not video.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    
    job_id = str(uuid.uuid4())
    ext = os.path.splitext(video.filename)[1].lower()
    
    is_video = ext in [".mp4", ".mov", ".mkv", ".webm"]
    is_audio = ext in [".wav", ".mp3", ".m4a", ".flac"]
    
    if not (is_video or is_audio):
        raise HTTPException(status_code=400, detail="Unsupported file format")
        
    file_path = os.path.join(UPLOADS_DIR, f"{job_id}{ext}")
    
    with open(file_path, "wb") as f:
        f.write(await video.read())
        
    # Start background processing
    background_tasks.add_task(process_meeting_background, job_id, file_path, is_video)
    
    return {"success": True, "job_id": job_id}

@router.get("/process/{job_id}")
async def get_status(job_id: str):
    status_file = os.path.join(OUTPUTS_DIR, f"{job_id}.json")
    if not os.path.exists(status_file):
        raise HTTPException(status_code=404, detail="Job not found")
        
    with open(status_file, "r") as f:
        data = json.load(f)
        
    return data

@router.get("/download/{job_id}/{format}")
async def download_results(job_id: str, format: str):
    if format not in ["json", "txt", "md"]:
        raise HTTPException(status_code=400, detail="Invalid format")
        
    file_path = os.path.join(OUTPUTS_DIR, f"{job_id}.{format}")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found or processing not complete")
        
    return FileResponse(file_path, filename=f"meeting_{job_id}.{format}")
