import os
import sqlite3
import json
import uuid
from datetime import datetime
import bcrypt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "traxion.db")
os.makedirs(DATA_DIR, exist_ok=True)

def get_db_connection():
    """Returns a SQLite connection with dict-like row factory."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes database schema and seeds initial admin account."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Detections Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                media_type TEXT NOT NULL,
                filename TEXT,
                posture TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                confidence REAL NOT NULL,
                inference_time_ms REAL DEFAULT 0,
                total_time_ms REAL DEFAULT 0,
                keypoints_detected INTEGER DEFAULT 0,
                impacted_zones TEXT,
                media_path TEXT,
                analyzed_media_path TEXT,
                reasoning_json TEXT,
                timeline_json TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_user_id ON detections(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp)")

        # Seed Default Admin if not exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            default_salt = bcrypt.gensalt(rounds=12)
            admin_pwd_hash = bcrypt.hashpw("Admin@Traxion2026".encode('utf-8'), default_salt).decode('utf-8')
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES ('admin', 'admin@traxion.ai', ?, 'admin')
            """, (admin_pwd_hash,))
            
        conn.commit()

# --- User Management ---

def create_user(username, email, password_hash, role='user'):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, (username, email, password_hash, role))
        conn.commit()
        return cursor.lastrowid

def get_user_by_username(username):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_email(email):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

# --- Detection History (Scoped strictly to user_id) ---

def save_detection(data: dict):
    detection_id = data.get("id") or str(uuid.uuid4())[:12]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO detections (
                id, user_id, media_type, filename, posture, risk_level, confidence,
                inference_time_ms, total_time_ms, keypoints_detected, impacted_zones,
                media_path, analyzed_media_path, reasoning_json, timeline_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            detection_id,
            data.get("user_id"),
            data.get("media_type", "image"),
            data.get("filename", "unknown"),
            data.get("posture", "NORMAL"),
            data.get("risk_level", "LOW"),
            data.get("confidence", 0.0),
            data.get("inference_time_ms", 0.0),
            data.get("total_time_ms", 0.0),
            data.get("keypoints_detected", 0),
            json.dumps(data.get("impacted_zones", [])),
            data.get("media_path"),
            data.get("analyzed_media_path"),
            json.dumps(data.get("reasoning", {})),
            json.dumps(data.get("timeline", []))
        ))
        conn.commit()
        return detection_id

def get_user_detections(user_id: int, limit: int = 50, offset: int = 0):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, timestamp, media_type, filename, posture, risk_level,
                   confidence, inference_time_ms, total_time_ms, keypoints_detected,
                   impacted_zones, media_path, analyzed_media_path
            FROM detections
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["impacted_zones"] = json.loads(d["impacted_zones"]) if d["impacted_zones"] else []
            results.append(d)
        return results

def get_detection_by_id(detection_id: str, user_id: int = None, is_admin: bool = False):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if is_admin:
            cursor.execute("SELECT * FROM detections WHERE id = ?", (detection_id,))
        else:
            cursor.execute("SELECT * FROM detections WHERE id = ? AND user_id = ?", (detection_id, user_id))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["impacted_zones"] = json.loads(d["impacted_zones"]) if d["impacted_zones"] else []
        d["reasoning"] = json.loads(d["reasoning_json"]) if d["reasoning_json"] else {}
        d["timeline"] = json.loads(d["timeline_json"]) if d["timeline_json"] else []
        return d

def delete_detection(detection_id: str, user_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Ensure user owns the record
        cursor.execute("SELECT media_path, analyzed_media_path FROM detections WHERE id = ? AND user_id = ?", (detection_id, user_id))
        row = cursor.fetchone()
        if not row:
            return False
        
        # Remove files if they exist
        for p in [row["media_path"], row["analyzed_media_path"]]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        cursor.execute("DELETE FROM detections WHERE id = ? AND user_id = ?", (detection_id, user_id))
        conn.commit()
        return True

# --- Admin Analytics (Privacy-Safe Aggregates) ---

def get_admin_metrics():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM detections")
        total_detections = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM detections WHERE risk_level = 'HIGH'")
        high_risk_detections = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM detections WHERE media_type = 'image'")
        images_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM detections WHERE media_type = 'video'")
        videos_count = cursor.fetchone()["count"]

        cursor.execute("SELECT AVG(inference_time_ms) as avg_inf FROM detections")
        avg_inf_row = cursor.fetchone()
        avg_inf_ms = round(avg_inf_row["avg_inf"] or 0, 1)

        # Recent risk distribution
        cursor.execute("""
            SELECT risk_level, COUNT(*) as count
            FROM detections
            GROUP BY risk_level
        """)
        risk_dist = {r["risk_level"]: r["count"] for r in cursor.fetchall()}

        return {
            "total_users": total_users,
            "total_detections": total_detections,
            "high_risk_detections": high_risk_detections,
            "images_analyzed": images_count,
            "videos_analyzed": videos_count,
            "average_inference_time_ms": avg_inf_ms,
            "risk_distribution": risk_dist,
            "system_status": "OPERATIONAL"
        }

# Run init on import
init_db()
