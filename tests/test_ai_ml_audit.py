import os
import cv2
import joblib
import numpy as np
import pytest
from ultralytics import YOLO
from backend.pipeline import RoadSentryAIEngine
from backend.kinematics import extract_biomechanical_features

class TestAIMLModelIntegrity:
    """Rigorous audit of Computer Vision models, classifiers, weights, and inference pipelines."""

    def test_yolo_model_artifact_exists_and_loads(self):
        model_path = "yolo11n-pose.pt"
        assert os.path.exists(model_path), f"YOLO model weights missing at: {model_path}"
        assert os.path.getsize(model_path) > 5 * 1024 * 1024, "YOLO weights file appears corrupted/incomplete"

        yolo = YOLO(model_path)
        assert yolo is not None
        assert hasattr(yolo, "predict")

    def test_classifier_pipeline_artifact_exists_and_loads(self):
        clf_path = os.path.join("models", "posture_classifier_95acc.pkl")
        assert os.path.exists(clf_path), f"Classifier artifact missing at: {clf_path}"
        assert os.path.getsize(clf_path) > 50 * 1024, "Classifier artifact too small"

        clf = joblib.load(clf_path)
        assert clf is not None
        assert hasattr(clf, "predict")
        assert hasattr(clf, "predict_proba")

        # Verify pipeline components
        assert hasattr(clf, "named_steps")
        assert "scaler" in clf.named_steps
        assert "clf" in clf.named_steps

    def test_classifier_feature_dimension_and_prediction(self):
        clf_path = os.path.join("models", "posture_classifier_95acc.pkl")
        clf = joblib.load(clf_path)

        # Test with exact 41-dimensional feature vector matching pipeline
        sample_feat = np.zeros((1, 41), dtype=np.float32)
        pred = clf.predict(sample_feat)
        probs = clf.predict_proba(sample_feat)

        assert pred[0] in [0, 1, 2], f"Unexpected class label: {pred[0]}"
        assert probs.shape == (1, 3), f"Expected probability shape (1, 3), got {probs.shape}"
        assert pytest.approx(float(np.sum(probs)), 0.01) == 1.0

    def test_edge_case_solid_black_frame(self):
        """Total camera occlusion / night time blackout."""
        engine = RoadSentryAIEngine(yolo_model="yolo11n-pose.pt", classifier_path=os.path.join("models", "posture_classifier_95acc.pkl"))
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", black_frame)

        result = engine.process_frame(buf.tobytes())
        # Should gracefully return detected=False without crashing
        assert result.get("detected") is False
        assert "inference_time_ms" in result

    def test_edge_case_solid_white_frame(self):
        """Total glare / overexposure."""
        engine = RoadSentryAIEngine(yolo_model="yolo11n-pose.pt", classifier_path=os.path.join("models", "posture_classifier_95acc.pkl"))
        white_frame = np.ones((480, 640, 3), dtype=np.uint8) * 255
        _, buf = cv2.imencode(".jpg", white_frame)

        result = engine.process_frame(buf.tobytes())
        assert result.get("detected") is False

    def test_edge_case_random_gaussian_noise(self):
        """Static noise / signal interference."""
        engine = RoadSentryAIEngine(yolo_model="yolo11n-pose.pt", classifier_path=os.path.join("models", "posture_classifier_95acc.pkl"))
        noise = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", noise)

        result = engine.process_frame(buf.tobytes())
        assert result.get("detected") is False

    def test_edge_case_corrupted_frame_bytes(self):
        """Corrupted network packet transmission."""
        engine = RoadSentryAIEngine(yolo_model="yolo11n-pose.pt", classifier_path=os.path.join("models", "posture_classifier_95acc.pkl"))
        corrupted_bytes = b"garbage_data_not_an_image_at_all_12345"

        result = engine.process_frame(corrupted_bytes)
        assert "error" in result
        assert result["error"] == "Invalid frame data"

    def test_real_sample_fall_inference(self):
        """Verifies detection on real verified road accident / fall image."""
        engine = RoadSentryAIEngine(yolo_model="yolo11n-pose.pt", classifier_path=os.path.join("models", "posture_classifier_95acc.pkl"))
        sample_path = os.path.join("frontend", "samples", "sample_fall.jpg")
        with open(sample_path, "rb") as f:
            img_bytes = f.read()

        report = engine.process_image(img_bytes, "sample_fall.jpg", "data/uploads", "data/outputs")
        assert report["posture"] == "FALL / ACCIDENT DETECTED"
        assert report["risk_level"] == "HIGH"
        assert report["keypoints_count"] >= 10
        assert report["confidence"] >= 0.90
        assert "Spine" in str(report["impacted_zones"]) or "Pelvis" in str(report["impacted_zones"])
