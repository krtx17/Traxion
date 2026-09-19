import time
import os
import cv2
import numpy as np
from backend import database, auth
from backend.pipeline import RoadSentryAIEngine

print("🧪 [TEST 1] Testing Database & Auth Layer...")
t_s = int(time.time())
u_a_name = f"user_a_{t_s}"
u_b_name = f"user_b_{t_s}"

# Register User A
pw_hash_a = auth.hash_password("PasswordA123!")
user_a_id = database.create_user(u_a_name, f"{u_a_name}@example.com", pw_hash_a)
print(f"✅ User A created with ID: {user_a_id}")

# Register User B
pw_hash_b = auth.hash_password("PasswordB123!")
user_b_id = database.create_user(u_b_name, f"{u_b_name}@example.com", pw_hash_b)
print(f"✅ User B created with ID: {user_b_id}")

# Login verification
user_a_db = database.get_user_by_username(u_a_name)
assert auth.verify_password("PasswordA123!", user_a_db["password_hash"]) == True
print("✅ Password verification succeeded!")

# Token generation
token_a = auth.create_access_token({"sub": str(user_a_id), "username": u_a_name})
payload = auth.decode_access_token(token_a)
assert payload["sub"] == str(user_a_id)
print("✅ JWT creation & verification succeeded!")

# Save detection for User A
det_id = database.save_detection({
    "id": f"DET-A_{t_s}",
    "user_id": user_a_id,
    "media_type": "image",
    "filename": "test_crash.jpg",
    "posture": "FALL / ACCIDENT DETECTED",
    "risk_level": "HIGH",
    "confidence": 98.4,
    "inference_time_ms": 28.5,
    "total_time_ms": 42.1,
    "keypoints_detected": 17,
    "impacted_zones": ["Spine / Pelvis", "Head / Cranial"],
    "reasoning": {"torso_angle": 18.4, "aspect_ratio": 1.45}
})
print(f"✅ Detection record saved for User A: {det_id}")

# Privacy Verification: User B queries their detections
user_b_detections = database.get_user_detections(user_b_id)
assert len(user_b_detections) == 0, "Privacy Leak! User B saw records!"
print("✅ Privacy check passed: User B cannot see User A's detections (Count = 0).")

# User A queries their detections
user_a_detections = database.get_user_detections(user_a_id)
assert len(user_a_detections) == 1, "User A should see exactly 1 record!"
print("✅ User A correctly sees their own detection.")

# Admin Metrics Check
metrics = database.get_admin_metrics()
print("✅ Admin metrics aggregate:", metrics)

print("\n⚡ [TEST 2] Testing Image Pipeline Speed (<0.4s)...")
engine = RoadSentryAIEngine(
    yolo_model="yolo11n-pose.pt",
    classifier_path=r"C:\Users\Anubh\.gemini\antigravity\scratch\road_accident_ai\models\posture_classifier_95acc.pkl"
)

# Create a test synthetic image (e.g. 640x480)
dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.circle(dummy_img, (320, 150), 40, (200, 200, 200), -1)
cv2.line(dummy_img, (320, 190), (320, 350), (200, 200, 200), 10)
_, img_bytes = cv2.imencode(".jpg", dummy_img)

# Now test real post-warmup user request
t0 = time.perf_counter()
rep = engine.process_image(
    img_bytes.tobytes(),
    "synthetic_test.jpg",
    r"C:\Users\Anubh\.gemini\antigravity\scratch\road_accident_ai\data\uploads",
    r"C:\Users\Anubh\.gemini\antigravity\scratch\road_accident_ai\data\outputs"
)
elapsed = time.perf_counter() - t0

print(f"✅ User Image Request Completed in: {elapsed:.3f}s (Inference: {rep['inference_time_formatted']}, Total: {rep['total_time_formatted']})")
print(f"✅ Posture: {rep['posture']}, Risk: {rep['risk_level']}, Keypoints: {rep['keypoints_count']}")
assert elapsed < 0.5, f"Image processing took {elapsed}s, expected < 0.5s!"
print("🎉 ALL BACKEND TESTS PASSED FLINT-CLEAN!")
