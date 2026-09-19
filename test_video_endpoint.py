import time
import os
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print("🧪 Testing Video Processing Endpoint (/api/detect/video)...")
sample_vid_path = os.path.join("frontend", "samples", "sample_accident.mp4")

with open(sample_vid_path, "rb") as f:
    t0 = time.perf_counter()
    res = client.post(
        "/api/detect/video",
        files={"file": ("sample_accident.mp4", f, "video/mp4")}
    )
    elapsed = time.perf_counter() - t0

assert res.status_code == 200, f"Video failed: {res.text}"
data = res.json()

print(f"✅ Video analysis finished in {elapsed:.2f}s!")
print(f"   Analyzed frames: {data['analyzed_frames']} / {data['total_frames']}")
print(f"   Posture: {data['posture']}")
print(f"   Risk Level: {data['risk_level']}")
print(f"   Video stream URL: {data['video_stream_url']}")
print(f"   Timeline events: {len(data['timeline'])}")
for ev in data['timeline'][:4]:
    print(f"     - [{ev.get('timestamp') or ev.get('time_sec')}] {ev.get('posture')} ({ev.get('risk_level')})")

print("🎉 Video endpoint verification successful!")
