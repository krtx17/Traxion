import os
import re
import time
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

class TestPathTraversalSecurity:
    """Tests designed to attempt directory and path traversal attacks."""

    @pytest.mark.parametrize("traversal_payload", [
        "../../../../windows/win.ini",
        "..\\..\\..\\..\\windows\\win.ini",
        "..%2F..%2F..%2Fwindows%2Fwin.ini",
        "....//....//....//windows//win.ini",
        "/etc/passwd",
        "C:\\boot.ini"
    ])
    def test_media_path_traversal_blocked(self, traversal_payload):
        # The endpoint should either sanitize via os.path.basename or return 404/400
        res = client.get(f"/api/media/output/{traversal_payload}")
        # Must never return 200 with sensitive host files
        assert res.status_code in [400, 404]

    def test_media_download_path_traversal_blocked(self):
        res = client.get("/api/media/download/output/../../main.py")
        assert res.status_code in [400, 404]


class TestIDORAndPrivilegeEscalation:
    """Tests ensuring users cannot access or tamper with other users' data or escalate privileges."""

    def test_idor_prevented_on_get_detection(self):
        # Create User A
        ts = int(time.time() * 1000)
        res_a = client.post("/api/auth/register", json={
            "username": f"user_idor_a_{ts}",
            "email": f"idor_a_{ts}@t.com",
            "password": "Password123!"
        })
        token_a = res_a.json()["token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Create User B
        res_b = client.post("/api/auth/register", json={
            "username": f"user_idor_b_{ts}",
            "email": f"idor_b_{ts}@t.com",
            "password": "Password123!"
        })
        token_b = res_b.json()["token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A performs image detection
        sample_path = os.path.join("frontend", "samples", "sample_fall.jpg")
        with open(sample_path, "rb") as f:
            det_res = client.post(
                "/api/detect/image",
                files={"file": ("sample_fall.jpg", f, "image/jpeg")},
                headers=headers_a
            )
        det_id = det_res.json()["job_id"]

        # User A can access own detection
        res_own = client.get(f"/api/detections/{det_id}", headers=headers_a)
        assert res_own.status_code == 200

        # User B attempts to access User A's detection -> MUST BE 404 / FORBIDDEN
        res_idor = client.get(f"/api/detections/{det_id}", headers=headers_b)
        assert res_idor.status_code == 404, f"IDOR vulnerability! User B accessed User A's detection: {res_idor.text}"

        # User B attempts to DELETE User A's detection -> MUST BE 404
        res_del_idor = client.delete(f"/api/detections/{det_id}", headers=headers_b)
        assert res_del_idor.status_code == 404, "IDOR vulnerability! User B deleted User A's detection!"

    def test_privilege_escalation_prevented_on_register(self):
        """User attempts to register with role='admin' in payload."""
        ts = int(time.time() * 1000)
        res = client.post("/api/auth/register", json={
            "username": f"hacker_{ts}",
            "email": f"hacker_{ts}@evil.com",
            "password": "Password123!",
            "role": "admin"
        })
        # Backend register endpoint should ignore 'role' and force 'user'
        data = res.json()
        assert data["user"]["role"] == "user", "Privilege escalation vulnerability! User became admin!"


class TestRepositorySecretScanning:
    """Scans repository source files for exposed API keys, private keys, and cloud secrets."""

    SUSPICIOUS_PATTERNS = [
        (r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/\+=]{40}['\"]", "AWS Secret Key"),
        (r"(?i)sk_live_[0-9a-zA-Z]{24}", "Stripe Live Secret"),
        (r"-----BEGIN RSA PRIVATE KEY-----", "RSA Private Key"),
        (r"-----BEGIN OPENSSH PRIVATE KEY-----", "SSH Private Key"),
        (r"(?i)ghp_[0-9a-zA-Z]{36}", "GitHub Personal Access Token"),
        (r"(?i)AIza[0-9A-Za-z-_]{35}", "Google API Key")
    ]

    def test_no_hardcoded_secrets_in_source(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_dirs = ["backend", "frontend"]

        findings = []
        for sdir in source_dirs:
            full_dir = os.path.join(base_dir, sdir)
            for root, _, files in os.walk(full_dir):
                for fname in files:
                    if fname.endswith((".py", ".js", ".html", ".json")):
                        fpath = os.path.join(root, fname)
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            for pat, name in self.SUSPICIOUS_PATTERNS:
                                if re.search(pat, content):
                                    findings.append((fname, name))

        assert len(findings) == 0, f"Exposed secrets detected: {findings}"
