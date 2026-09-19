import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from backend.pipeline import TraxionEngine, RoadSentryAIEngine
from backend import database, auth

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
MODEL_PATH = os.path.join(BASE_DIR, "models", "posture_classifier_95acc.pkl")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------------------------------------------
# FastAPI Application Setup
# -------------------------------------------------------------
app = FastAPI(
    title="Traxion - Real-Time Biomechanical Movement & Posture Intelligence",
    version="3.0.0",
    description="Real-Time 17-Keypoint Biomechanical Movement & Risk Intelligence"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Singleton Computer Vision Engine ONCE
engine = TraxionEngine(yolo_model="yolo11n-pose.pt", classifier_path=MODEL_PATH)

# Mount Static Frontend
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# -------------------------------------------------------------
# Request / Response Schemas
# -------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class LiveFrameRequest(BaseModel):
    image_base64: str

# -------------------------------------------------------------
# Root & System Health
# -------------------------------------------------------------
@app.get("/")
async def root():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Traxion API is Running."}

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "system": "Traxion",
        "yolo_pose": "ready",
        "ml_classifier_loaded": engine.classifier is not None,
        "database": "sqlite_ready"
    }

# -------------------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------------------
@app.post("/api/auth/register")
async def register(payload: RegisterRequest):
    # Validation
    if len(payload.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters long.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    if database.get_user_by_username(payload.username):
        raise HTTPException(status_code=400, detail="Username is already registered.")
    if database.get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email is already registered.")

    hashed_pw = auth.hash_password(payload.password)
    user_id = database.create_user(payload.username, payload.email, hashed_pw, role='user')

    token = auth.create_access_token({"sub": str(user_id), "username": payload.username, "role": "user"})
    return {
        "message": "User registered successfully.",
        "token": token,
        "user": {
            "id": user_id,
            "username": payload.username,
            "email": payload.email,
            "role": "user"
        }
    }

@app.post("/api/auth/login")
async def login(payload: LoginRequest):
    user = database.get_user_by_username(payload.username)
    if not user or not auth.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = auth.create_access_token({"sub": str(user["id"]), "username": user["username"], "role": user["role"]})
    return {
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    }

@app.get("/api/auth/me")
async def get_me(user: dict = Depends(auth.get_current_user)):
    return {"user": user}

# -------------------------------------------------------------
# Computer Vision Detection Endpoints
# -------------------------------------------------------------

# 1. IMAGE INFERENCE (<0.4s) with Full Visual Reasoning & Before/After
@app.post("/api/detect/image")
async def detect_image(
    file: UploadFile = File(...),
    user: dict | None = Depends(auth.get_optional_user)
):
    if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
        raise HTTPException(status_code=400, detail="Unsupported image format. Upload JPG, PNG, or WEBP.")

    try:
        image_bytes = await file.read()
        if len(image_bytes) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image exceeds maximum file size (25MB).")

        # Ultra-fast in-memory processing
        report = engine.process_image(image_bytes, file.filename, UPLOAD_DIR, OUTPUT_DIR)

        # Save to database scoped to authenticated user (or guest)
        db_record = {
            "id": report["job_id"],
            "user_id": user["id"] if user else None,
            "media_type": "image",
            "filename": file.filename,
            "posture": report["posture"],
            "risk_level": report["risk_level"],
            "confidence": report["confidence"],
            "inference_time_ms": report["inference_time_ms"],
            "total_time_ms": report["total_time_ms"],
            "keypoints_detected": report["keypoints_count"],
            "impacted_zones": report["impacted_zones"],
            "media_path": report["media_path"],
            "analyzed_media_path": report["analyzed_media_path"],
            "reasoning": report["reasoning"]
        }
        database.save_detection(db_record)

        return JSONResponse(content=report)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image inference error: {str(e)}")

# 2. VIDEO INFERENCE with Progress Stride & Event Timeline
@app.post("/api/detect/video")
async def detect_video(
    file: UploadFile = File(...),
    user: dict | None = Depends(auth.get_optional_user)
):
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
        raise HTTPException(status_code=400, detail="Unsupported video format. Upload MP4, AVI, or MOV.")

    job_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename)[-1]
    input_file_path = os.path.join(UPLOAD_DIR, f"input_{job_id}{ext}")
    output_filename = f"analyzed_{job_id}.mp4"
    output_file_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        with open(input_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        report = engine.process_video(input_file_path, output_file_path)
        report["job_id"] = job_id
        report["original_filename"] = file.filename
        report["video_stream_url"] = f"/api/media/output/{output_filename}"
        report["download_url"] = f"/api/media/download/output/{output_filename}"

        # Save to database
        db_record = {
            "id": job_id,
            "user_id": user["id"] if user else None,
            "media_type": "video",
            "filename": file.filename,
            "posture": report["posture"],
            "risk_level": report["risk_level"],
            "confidence": report["confidence"],
            "inference_time_ms": report["processing_time_sec"] * 1000,
            "total_time_ms": report["processing_time_sec"] * 1000,
            "keypoints_detected": 17,
            "impacted_zones": report["impacted_zones"],
            "media_path": input_file_path,
            "analyzed_media_path": output_file_path,
            "timeline": report["timeline"]
        }
        database.save_detection(db_record)

        return JSONResponse(content=report)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video processing error: {str(e)}")

# 3. LIVE CAMERA FRAME INFERENCE (<30ms)
@app.post("/api/detect/frame")
async def detect_frame(payload: LiveFrameRequest):
    try:
        # Strip data URL header if present
        data = payload.image_base64
        if "base64," in data:
            data = data.split("base64,")[1]
        import base64
        frame_bytes = base64.b64decode(data)

        result = engine.process_frame(frame_bytes)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

# -------------------------------------------------------------
# User Scoped Detections History (Privacy Enforced)
# -------------------------------------------------------------
@app.get("/api/detections")
async def list_user_detections(
    user: dict = Depends(auth.get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Returns only the authenticated user's detections."""
    history = database.get_user_detections(user["id"], limit=limit, offset=offset)
    return {"detections": history, "count": len(history)}

@app.get("/api/detections/{detection_id}")
async def get_detection(
    detection_id: str,
    user: dict = Depends(auth.get_current_user)
):
    """Retrieves a single detection owned by current user (or admin)."""
    is_admin = user.get("role") == "admin"
    record = database.get_detection_by_id(detection_id, user_id=user["id"], is_admin=is_admin)
    if not record:
        raise HTTPException(status_code=404, detail="Detection record not found or access denied.")
    return {"detection": record}

@app.delete("/api/detections/{detection_id}")
async def remove_detection(
    detection_id: str,
    user: dict = Depends(auth.get_current_user)
):
    """Deletes a detection and its files if owned by user."""
    success = database.delete_detection(detection_id, user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Record not found or unauthorized.")
    return {"message": "Detection record and associated media deleted successfully."}

# -------------------------------------------------------------
# Admin Analytics Dashboard (Role Checked & Privacy-Preserving)
# -------------------------------------------------------------
@app.get("/api/admin/overview")
async def admin_overview(admin: dict = Depends(auth.get_current_admin)):
    """Provides system analytics without exposing users' private media."""
    metrics = database.get_admin_metrics()
    return {"metrics": metrics}

# -------------------------------------------------------------
# Secure Media Delivery (Prevents Path Traversal)
# -------------------------------------------------------------
@app.api_route("/api/media/{folder}/{filename}", methods=["GET", "HEAD"])
async def serve_media(folder: str, filename: str):
    if folder not in ["upload", "output"]:
        raise HTTPException(status_code=400, detail="Invalid media folder.")

    # Sanitize filename
    clean_name = os.path.basename(filename)
    base_folder = UPLOAD_DIR if folder == "upload" else OUTPUT_DIR
    target_path = os.path.join(base_folder, clean_name)

    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Requested media file not found.")

    media_type = "video/mp4" if clean_name.endswith(('.mp4', '.avi', '.mov')) else "image/jpeg"
    return FileResponse(
        target_path, 
        media_type=media_type, 
        headers={"Accept-Ranges": "bytes"}
    )

@app.api_route("/api/media/download/{folder}/{filename}", methods=["GET", "HEAD"])
async def download_media(folder: str, filename: str):
    if folder not in ["upload", "output"]:
        raise HTTPException(status_code=400, detail="Invalid media folder.")

    clean_name = os.path.basename(filename)
    base_folder = UPLOAD_DIR if folder == "upload" else OUTPUT_DIR
    target_path = os.path.join(base_folder, clean_name)

    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Requested media file not found.")

    media_type = "video/mp4" if clean_name.endswith(('.mp4', '.avi', '.mov')) else "image/jpeg"
    return FileResponse(
        target_path,
        media_type=media_type,
        filename=clean_name,
        headers={"Accept-Ranges": "bytes"}
    )

# Emergency SOS Simulation Endpoint
@app.post("/api/dispatch-sos")
async def dispatch_sos(payload: dict):
    level = payload.get("level", "CRITICAL")
    lat = payload.get("lat", 28.6139)
    lng = payload.get("lng", 77.2090)
    address = payload.get("address", "Expressway Corridor, KM Marker 42")

    if level == "CRITICAL":
        units = ["ALS Critical Trauma Unit #08", "Spinal Immobilization Specialist", "Highway Rescue Van #03"]
        nearest_hospital = "Apex Level-1 Emergency Trauma Center"
        eta = 6
    elif level == "WARNING":
        units = ["BLS Rapid Response Ambulance #14", "Paramedic First Responder"]
        nearest_hospital = "Metro Highway Healthcare Facility"
        eta = 9
    else:
        units = ["Highway Safety Patrol Unit #02"]
        nearest_hospital = "District Medical Aid Station"
        eta = 12

    return {
        "dispatch_id": f"SOS-{uuid.uuid4().hex[:6].upper()}",
        "status": "DISPATCHED",
        "priority": level,
        "nearest_hospital": nearest_hospital,
        "location": {
            "address": address,
            "coordinates": f"{lat:.4f}° N, {lng:.4f}° E" if isinstance(lat, (int, float)) and isinstance(lng, (int, float)) else "28.6139° N, 77.2090° E"
        },
        "units_deployed": units,
        "estimated_arrival_minutes": eta,
        "emergency_helpline": "108",
        "details_forwarded": payload
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
