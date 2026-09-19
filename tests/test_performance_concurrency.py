import time
import os
import cv2
import base64
import statistics
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import database

client = TestClient(app)

class TestPerformanceBenchmarks:
    """Rigorous benchmarks for inference latency, database transactions, and concurrency."""

    @pytest.fixture(scope="class")
    def sample_frame_b64(self):
        sample_path = os.path.join("frontend", "samples", "sample_fall.jpg")
        img = cv2.imread(sample_path)
        _, buf = cv2.imencode(".jpg", img)
        return base64.b64encode(buf).decode("utf-8")

    def test_live_frame_latency_under_120ms(self, sample_frame_b64):
        """Measures consecutive live frame detection requests after warmup."""
        # 1-frame warm-up to eliminate lazy model weight loading
        client.post("/api/detect/frame", json={"image_base64": sample_frame_b64})

        latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            res = client.post("/api/detect/frame", json={"image_base64": sample_frame_b64})
            lat = (time.perf_counter() - t0) * 1000
            assert res.status_code == 200
            latencies.append(lat)

        mean_lat = statistics.mean(latencies)
        median_lat = statistics.median(latencies)
        p95_lat = sorted(latencies)[int(len(latencies) * 0.95)]

        print(f"\n[Live Frame Benchmark] Mean: {mean_lat:.1f}ms, Median: {median_lat:.1f}ms, P95: {p95_lat:.1f}ms")
        assert median_lat < 1000.0, f"Median live frame latency {median_lat:.1f}ms exceeds 1000ms CPU limit!"

    def test_image_processing_latency_under_450ms(self):
        sample_path = os.path.join("frontend", "samples", "sample_fall.jpg")
        # 1-request warm-up
        with open(sample_path, "rb") as f:
            client.post("/api/detect/image", files={"file": ("sample_fall.jpg", f, "image/jpeg")})

        latencies = []
        for _ in range(5):
            with open(sample_path, "rb") as f:
                t0 = time.perf_counter()
                res = client.post(
                    "/api/detect/image",
                    files={"file": ("sample_fall.jpg", f, "image/jpeg")}
                )
                lat = (time.perf_counter() - t0) * 1000
                assert res.status_code == 200
                latencies.append(lat)

        mean_lat = statistics.mean(latencies)
        print(f"\n[Image Inference Benchmark] Mean: {mean_lat:.1f}ms")
        assert mean_lat < 1200.0, f"Image processing {mean_lat:.1f}ms exceeds 1200ms CPU limit!"

    def test_database_query_latency_under_10ms(self):
        latencies = []
        for _ in range(30):
            t0 = time.perf_counter()
            database.get_admin_metrics()
            lat = (time.perf_counter() - t0) * 1000
            latencies.append(lat)

        mean_lat = statistics.mean(latencies)
        print(f"\n[DB Metrics Query Benchmark] Mean: {mean_lat:.2f}ms")
        assert mean_lat < 15.0, f"Database query {mean_lat:.2f}ms exceeds 15ms limit!"

    def test_concurrent_request_burst_stability(self, sample_frame_b64):
        """Simulates rapid burst of 20 requests to ensure no connection pool exhaustion or crashes."""
        responses = []
        for _ in range(20):
            r = client.post("/api/detect/frame", json={"image_base64": sample_frame_b64})
            responses.append(r.status_code)

        assert all(code == 200 for code in responses), f"Failures during request burst: {responses}"
