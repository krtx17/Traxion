import time
import os
import base64
import pytest
import cv2
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def authenticated_client():
    ts = int(time.time() * 1000)
    u_name = f"api_user_{ts}"
    pwd = "ApiUserPass123!"
    reg_res = client.post("/api/auth/register", json={
        "username": u_name,
        "email": f"{u_name}@test.com",
        "password": pwd
    })
    token = reg_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers, u_name

@pytest.fixture(scope="module")
def admin_client():
    admin_res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "Admin@RoadSentry2026"
    })
    token = admin_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers

class TestSystemAndRootEndpoints:
    def test_root_serves_html(self):
        res = client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "ROADSENTRY" in res.text

    def test_health_check(self):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "online"
        assert data["system"] == "RoadSentry AI"
        assert data["yolo_pose"] == "ready"
        assert data["ml_classifier_loaded"] is True
        assert data["database"] == "sqlite_ready"

    def test_static_app_js(self):
        res = client.get("/static/app.js")
        assert res.status_code == 200
        assert "AppState" in res.text

    def test_static_nonexistent(self):
        res = client.get("/static/nonexistent_file.xyz")
        assert res.status_code == 404


class TestAuthenticationEndpoints:
    def test_register_success(self):
        ts = int(time.time() * 1000)
        res = client.post("/api/auth/register", json={
            "username": f"new_user_{ts}",
            "email": f"new_{ts}@test.com",
            "password": "Password123!"
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["user"]["role"] == "user"

    def test_register_short_username_rejected(self):
        res = client.post("/api/auth/register", json={
            "username": "ab",
            "email": "ab@test.com",
            "password": "Password123!"
        })
        assert res.status_code == 400
        assert "at least 3 characters" in res.json()["detail"]

    def test_register_short_password_rejected(self):
        res = client.post("/api/auth/register", json={
            "username": "valid_user",
            "email": "valid@test.com",
            "password": "123"
        })
        assert res.status_code == 400
        assert "at least 6 characters" in res.json()["detail"]

    def test_register_invalid_email_format(self):
        res = client.post("/api/auth/register", json={
            "username": "valid_user_2",
            "email": "not-an-email",
            "password": "Password123!"
        })
        assert res.status_code == 422  # Pydantic EmailStr validation

    def test_login_invalid_credentials(self):
        res = client.post("/api/auth/login", json={
            "username": "non_existent_user_999",
            "password": "WrongPassword!"
        })
        assert res.status_code == 401

    def test_auth_me_unauthorized(self):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_auth_me_authorized(self, authenticated_client):
        c, headers, u_name = authenticated_client
        res = c.get("/api/auth/me", headers=headers)
        assert res.status_code == 200
        assert res.json()["user"]["username"] == u_name


class TestDetectionStudioEndpoints:
    def test_detect_image_valid(self, authenticated_client):
        c, headers, _ = authenticated_client
        sample_path = os.path.join("frontend", "samples", "sample_fall.jpg")
        with open(sample_path, "rb") as f:
            res = c.post(
                "/api/detect/image",
                files={"file": ("sample_fall.jpg", f, "image/jpeg")},
                headers=headers
            )
        assert res.status_code == 200
        data = res.json()
        assert "job_id" in data
        assert "posture" in data
        assert "confidence" in data
        assert "keypoints" in data
        assert "analyzed_image_base64" in data
        assert data["keypoints_count"] == 17

    def test_detect_image_unsupported_format(self, authenticated_client):
        c, headers, _ = authenticated_client
        res = c.post(
            "/api/detect/image",
            files={"file": ("malicious.exe", b"binary content", "application/octet-stream")},
            headers=headers
        )
        assert res.status_code == 400
        assert "Unsupported image format" in res.json()["detail"]

    def test_detect_frame_valid(self):
        sample_path = os.path.join("frontend", "samples", "sample_fall.jpg")
        img = cv2.imread(sample_path)
        _, buf = cv2.imencode(".jpg", img)
        b64_str = base64.b64encode(buf).decode("utf-8")

        res = client.post("/api/detect/frame", json={"image_base64": b64_str})
        assert res.status_code == 200
        data = res.json()
        assert data["detected"] is True
        assert "posture" in data
        assert "torso_angle" in data
        assert "fps" in data

    def test_detect_frame_empty_payload(self):
        res = client.post("/api/detect/frame", json={"image_base64": ""})
        assert res.status_code == 400

    def test_detect_video_unsupported_format(self):
        res = client.post(
            "/api/detect/video",
            files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")}
        )
        assert res.status_code == 400


class TestMediaStreamingAndDownloadEndpoints:
    def test_media_streaming_range_and_head(self):
        # We know test_verify_h264.mp4 exists in data/outputs
        res_head = client.head("/api/media/output/test_verify_h264.mp4")
        assert res_head.status_code == 200
        assert res_head.headers.get("accept-ranges") == "bytes"
        assert "video/mp4" in res_head.headers.get("content-type")

    def test_media_download_endpoint(self):
        res = client.head("/api/media/download/output/test_verify_h264.mp4")
        assert res.status_code == 200
        assert "attachment" in res.headers.get("content-disposition", "")
        assert "test_verify_h264.mp4" in res.headers.get("content-disposition", "")

    def test_media_invalid_folder_rejected(self):
        res = client.get("/api/media/system_internal/passwords.txt")
        assert res.status_code == 400

    def test_media_nonexistent_file_404(self):
        res = client.get("/api/media/output/nonexistent_xyz_123.mp4")
        assert res.status_code == 404


class TestAdminAndEmergencyEndpoints:
    def test_admin_overview_forbidden_for_normal_user(self, authenticated_client):
        c, headers, _ = authenticated_client
        res = c.get("/api/admin/overview", headers=headers)
        assert res.status_code == 403

    def test_admin_overview_allowed_for_admin(self, admin_client):
        c, headers = admin_client
        res = c.get("/api/admin/overview", headers=headers)
        assert res.status_code == 200
        assert "metrics" in res.json()

    def test_dispatch_sos_simulation(self):
        res = client.post("/api/dispatch-sos", json={"level": "CRITICAL", "notes": "Highway crash"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DISPATCHED"
        assert data["priority"] == "CRITICAL"
        assert len(data["units_deployed"]) > 0
