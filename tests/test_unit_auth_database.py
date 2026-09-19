import os
import time
import sqlite3
import pytest
import jwt
from fastapi import HTTPException
from backend import auth, database

class TestAuthSecurity:
    """Unit tests for hashing, JWT handling, and password validation."""

    def test_bcrypt_hash_and_verify(self):
        password = "SecurePassword@2026"
        hashed = auth.hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert auth.verify_password(password, hashed) is True
        assert auth.verify_password("WrongPassword123", hashed) is False

    def test_verify_password_corrupted_hash(self):
        assert auth.verify_password("Password", "not_a_valid_bcrypt_hash") is False
        assert auth.verify_password("Password", "") is False

    def test_jwt_token_lifecycle(self):
        data = {"sub": "42", "username": "audit_user", "role": "user"}
        token = auth.create_access_token(data)
        assert isinstance(token, str)

        payload = auth.decode_access_token(token)
        assert payload["sub"] == "42"
        assert payload["username"] == "audit_user"
        assert payload["role"] == "user"
        assert "exp" in payload

    def test_jwt_tampered_token(self):
        data = {"sub": "42", "username": "normal_user", "role": "user"}
        token = auth.create_access_token(data)
        # Tamper with the token signature
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.bad_signature_tampered"
        with pytest.raises(HTTPException) as exc:
            auth.decode_access_token(tampered_token)
        assert exc.value.status_code == 401

    def test_jwt_malformed_token(self):
        with pytest.raises(HTTPException) as exc:
            auth.decode_access_token("this-is-not-a-jwt")
        assert exc.value.status_code == 401


class TestDatabaseLayer:
    """Unit tests for SQLite CRUD, data constraints, and privacy boundaries."""

    def test_create_and_fetch_user(self):
        ts = int(time.time() * 1000)
        username = f"dbuser_{ts}"
        email = f"{username}@test.com"
        pwd_hash = auth.hash_password("Pass1234!")

        user_id = database.create_user(username, email, pwd_hash, role="user")
        assert user_id > 0

        # Fetch by username
        u1 = database.get_user_by_username(username)
        assert u1 is not None
        assert u1["id"] == user_id
        assert u1["email"] == email

        # Fetch by email
        u2 = database.get_user_by_email(email)
        assert u2 is not None
        assert u2["id"] == user_id

        # Fetch by ID
        u3 = database.get_user_by_id(user_id)
        assert u3 is not None
        assert u3["username"] == username

    def test_unique_username_constraint(self):
        ts = int(time.time() * 1000)
        username = f"dupuser_{ts}"
        pwd_hash = auth.hash_password("Pass1234!")
        database.create_user(username, f"{username}_1@test.com", pwd_hash)

        with pytest.raises(sqlite3.IntegrityError):
            database.create_user(username, f"{username}_2@test.com", pwd_hash)

    def test_unique_email_constraint(self):
        ts = int(time.time() * 1000)
        email = f"dupemail_{ts}@test.com"
        pwd_hash = auth.hash_password("Pass1234!")
        database.create_user(f"user1_{ts}", email, pwd_hash)

        with pytest.raises(sqlite3.IntegrityError):
            database.create_user(f"user2_{ts}", email, pwd_hash)

    def test_detection_user_isolation(self):
        ts = int(time.time() * 1000)
        u1_id = database.create_user(f"iso1_{ts}", f"iso1_{ts}@t.com", "hash")
        u2_id = database.create_user(f"iso2_{ts}", f"iso2_{ts}@t.com", "hash")

        det_id_1 = database.save_detection({
            "id": f"det_{ts}_1",
            "user_id": u1_id,
            "media_type": "image",
            "posture": "NORMAL POSTURE",
            "risk_level": "LOW",
            "confidence": 0.95
        })

        # User 1 should see detection
        u1_dets = database.get_user_detections(u1_id)
        assert any(d["id"] == det_id_1 for d in u1_dets)

        # User 2 MUST NOT see User 1's detection
        u2_dets = database.get_user_detections(u2_id)
        assert not any(d["id"] == det_id_1 for d in u2_dets)

        # Direct fetch by ID with user ownership check
        assert database.get_detection_by_id(det_id_1, user_id=u1_id) is not None
        assert database.get_detection_by_id(det_id_1, user_id=u2_id) is None  # IDOR blocked

    def test_admin_bypass_for_investigation(self):
        ts = int(time.time() * 1000)
        u_id = database.create_user(f"user_adm_{ts}", f"user_adm_{ts}@t.com", "hash")
        det_id = database.save_detection({
            "id": f"det_adm_{ts}",
            "user_id": u_id,
            "media_type": "video",
            "posture": "FALL / ACCIDENT DETECTED",
            "risk_level": "HIGH",
            "confidence": 0.98
        })
        # Admin can view regardless of user_id
        admin_view = database.get_detection_by_id(det_id, user_id=None, is_admin=True)
        assert admin_view is not None
        assert admin_view["id"] == det_id

    def test_delete_detection_and_file_cleanup(self, tmp_path):
        ts = int(time.time() * 1000)
        u_id = database.create_user(f"del_{ts}", f"del_{ts}@t.com", "hash")

        # Create temporary dummy media files
        fake_upload = tmp_path / "fake_input.jpg"
        fake_output = tmp_path / "fake_output.jpg"
        fake_upload.write_text("dummy image data")
        fake_output.write_text("annotated dummy image data")

        det_id = database.save_detection({
            "id": f"det_del_{ts}",
            "user_id": u_id,
            "media_type": "image",
            "posture": "NORMAL",
            "risk_level": "LOW",
            "confidence": 0.9,
            "media_path": str(fake_upload),
            "analyzed_media_path": str(fake_output)
        })

        assert os.path.exists(fake_upload)
        assert os.path.exists(fake_output)

        # Delete detection
        deleted = database.delete_detection(det_id, user_id=u_id)
        assert deleted is True

        # Files must be cleaned up from disk
        assert not os.path.exists(fake_upload)
        assert not os.path.exists(fake_output)

        # Record must be gone from DB
        assert database.get_detection_by_id(det_id, user_id=u_id) is None

    def test_sql_injection_defense(self):
        """Verify parameterized queries resist SQL injection attacks."""
        sqli_payload = "admin' OR '1'='1"
        res = database.get_user_by_username(sqli_payload)
        assert res is None, "SQL injection succeeded in get_user_by_username!"

        sqli_email = "test@example.com' UNION SELECT * FROM users; --"
        res_email = database.get_user_by_email(sqli_email)
        assert res_email is None, "SQL injection succeeded in get_user_by_email!"
