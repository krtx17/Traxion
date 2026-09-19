import time
import os
import json
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print("🧪 [1] Testing Root & Static Mounting...")
res = client.get("/")
assert res.status_code == 200, f"Root failed: {res.status_code}"
assert "RoadSentry" in res.text, "Title or brand not found in HTML"
print("✅ Root HTML rendered successfully.")

res_js = client.get("/static/app.js")
assert res_js.status_code == 200, f"app.js failed: {res_js.status_code}"
assert "AppState" in res_js.text, "app.js content not found"
print("✅ Static frontend/app.js served successfully.")

print("\n🧪 [2] Testing System Health Check...")
res = client.get("/api/health")
assert res.status_code == 200
data = res.json()
assert data["status"] == "online"
assert data["system"] == "RoadSentry AI"
print(f"✅ Health status: {data}")

print("\n🧪 [3] Testing Authentication Flow...")
ts = int(time.time())
u_name = f"tester_{ts}"
# Register
reg_res = client.post("/api/auth/register", json={
    "username": u_name,
    "email": f"{u_name}@test.com",
    "password": "SecurePassword123!"
})
assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
token = reg_res.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ User registered and token received.")

# Login
login_res = client.post("/api/auth/login", json={
    "username": u_name,
    "password": "SecurePassword123!"
})
assert login_res.status_code == 200
print("✅ Login verified.")

# /api/auth/me
me_res = client.get("/api/auth/me", headers=headers)
assert me_res.status_code == 200
assert me_res.json()["user"]["username"] == u_name
print("✅ /api/auth/me verified.")

print("\n🧪 [4] Testing Image Detection Studio (/api/detect/image)...")
sample_img_path = os.path.join("frontend", "samples", "sample_fall.jpg")
with open(sample_img_path, "rb") as f:
    t0 = time.perf_counter()
    img_res = client.post(
        "/api/detect/image",
        files={"file": ("sample_fall.jpg", f, "image/jpeg")},
        headers=headers
    )
    t_elapsed = time.perf_counter() - t0

assert img_res.status_code == 200, f"Image detect failed: {img_res.text}"
img_data = img_res.json()
print(f"✅ Image processed in {t_elapsed:.3f}s client time!")
print(f"   Inference Time: {img_data['inference_time_formatted']}")
print(f"   Total Time: {img_data['total_time_formatted']}")
print(f"   Posture: {img_data['posture']}")
print(f"   Risk: {img_data['risk_level']}")
print(f"   Reasoning: {img_data['reasoning']['diagnostic_summary']}")
print(f"   Keypoints count: {len(img_data['keypoints'])}")
assert img_data['inference_time_ms'] < 400, f"Inference took {img_data['inference_time_ms']}ms, expected <400ms!"

print("\n🧪 [5] Testing Live Frame Stream (/api/detect/frame)...")
import cv2, base64
dummy_frame = cv2.imread(sample_img_path)
_, buf = cv2.imencode(".jpg", dummy_frame)
b64_str = base64.b64encode(buf).decode("utf-8")

t0 = time.perf_counter()
frame_res = client.post("/api/detect/frame", json={"image_base64": b64_str})
t_frame = (time.perf_counter() - t0) * 1000
assert frame_res.status_code == 200
f_data = frame_res.json()
print(f"✅ Live frame processed in {t_frame:.1f}ms! Posture: {f_data['posture']}, Risk: {f_data['risk_level']}")

print("\n🧪 [6] Testing User Scoped History & Isolation...")
hist_res = client.get("/api/detections", headers=headers)
assert hist_res.status_code == 200
hist_data = hist_res.json()
assert hist_data["count"] >= 1, "User should have at least 1 detection recorded"
det_id = hist_data["detections"][0]["id"]
print(f"✅ User detection record retrieved: ID {det_id}")

print("\n🧪 [7] Testing Admin Overview & Seeding...")
# Login as pre-seeded admin
admin_res = client.post("/api/auth/login", json={
    "username": "admin",
    "password": "Admin@RoadSentry2026"
})
assert admin_res.status_code == 200, f"Admin login failed: {admin_res.text}"
admin_token = admin_res.json()["token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}

overview_res = client.get("/api/admin/overview", headers=admin_headers)
assert overview_res.status_code == 200
ov_data = overview_res.json()
print(f"✅ Admin analytics metrics: {ov_data['metrics']}")

print("\n🎉 ALL FULL SYSTEM INTEGRATION TESTS PASSED 100%!")
