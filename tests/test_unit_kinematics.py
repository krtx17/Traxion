import pytest
import numpy as np
from backend.kinematics import calculate_angle, extract_biomechanical_features, KEYPOINTS_MAP

class TestKinematicsCalculations:
    """Unit tests for anatomical joint angle and geometric calculations."""

    def test_calculate_angle_right_angle(self):
        p1 = [0.0, 1.0]
        p2 = [0.0, 0.0]
        p3 = [1.0, 0.0]
        ang = calculate_angle(p1, p2, p3)
        assert pytest.approx(ang, 0.01) == 90.0

    def test_calculate_angle_straight_line_180(self):
        p1 = [-1.0, 0.0]
        p2 = [0.0, 0.0]
        p3 = [1.0, 0.0]
        ang = calculate_angle(p1, p2, p3)
        assert pytest.approx(ang, 0.01) == 180.0

    def test_calculate_angle_acute_45(self):
        p1 = [1.0, 1.0]
        p2 = [0.0, 0.0]
        p3 = [1.0, 0.0]
        ang = calculate_angle(p1, p2, p3)
        assert pytest.approx(ang, 0.1) == 45.0

    def test_calculate_angle_zero_norm_degenerate(self):
        # Identical points (p1 == p2)
        p1 = [5.0, 5.0]
        p2 = [5.0, 5.0]
        p3 = [10.0, 5.0]
        ang = calculate_angle(p1, p2, p3)
        # Should gracefully return fallback 90.0 without division by zero
        assert ang == 90.0

    def test_calculate_angle_all_zeros(self):
        p1 = [0.0, 0.0]
        p2 = [0.0, 0.0]
        p3 = [0.0, 0.0]
        ang = calculate_angle(p1, p2, p3)
        assert ang == 90.0

    def test_calculate_angle_negative_coordinates(self):
        p1 = [-5.0, -10.0]
        p2 = [-5.0, -5.0]
        p3 = [-10.0, -5.0]
        ang = calculate_angle(p1, p2, p3)
        assert pytest.approx(ang, 0.01) == 90.0


class TestBiomechanicalFeatureExtraction:
    """Unit tests for 45-dimensional feature vector extraction and posture diagnostics."""

    @pytest.fixture
    def default_upright_person(self):
        # 17 Keypoints in standard COCO format: [x, y]
        # Upright standing person in 640x480 frame
        kpts = np.zeros((17, 2), dtype=np.float32)
        # Head
        kpts[0] = [320, 80]   # nose
        kpts[1] = [315, 75]   # l_eye
        kpts[2] = [325, 75]   # r_eye
        kpts[3] = [305, 80]   # l_ear
        kpts[4] = [335, 80]   # r_ear
        # Shoulders
        kpts[5] = [280, 140]  # l_shoulder
        kpts[6] = [360, 140]  # r_shoulder
        # Elbows
        kpts[7] = [260, 220]  # l_elbow
        kpts[8] = [380, 220]  # r_elbow
        # Wrists
        kpts[9] = [250, 300]  # l_wrist
        kpts[10] = [390, 300] # r_wrist
        # Hips
        kpts[11] = [290, 280] # l_hip
        kpts[12] = [350, 280] # r_hip
        # Knees
        kpts[13] = [295, 380] # l_knee
        kpts[14] = [345, 380] # r_knee
        # Ankles
        kpts[15] = [295, 460] # l_ankle
        kpts[16] = [345, 460] # r_ankle

        confs = np.ones(17, dtype=np.float32) * 0.95
        bbox = np.array([240, 60, 400, 470], dtype=np.int32)
        return kpts, confs, bbox

    def test_feature_vector_dimensionality(self, default_upright_person):
        kpts, confs, bbox = default_upright_person
        feat, diag = extract_biomechanical_features(kpts, confs, bbox)

        assert feat.shape == (1, 41), f"Expected shape (1, 41), got {feat.shape}"
        assert feat.dtype == np.float32
        assert not np.isnan(feat).any(), "Feature vector contains NaN values"
        assert not np.isinf(feat).any(), "Feature vector contains Inf values"

    def test_diagnostic_keys_and_types(self, default_upright_person):
        kpts, confs, bbox = default_upright_person
        _, diag = extract_biomechanical_features(kpts, confs, bbox)

        expected_keys = [
            "torso_angle", "aspect_ratio", "left_knee_angle", "right_knee_angle",
            "left_elbow_angle", "right_elbow_angle", "is_upper_body_only", "is_horizontal"
        ]
        for k in expected_keys:
            assert k in diag, f"Missing diagnostic key: {k}"
        assert isinstance(diag["is_horizontal"], bool)
        assert isinstance(diag["is_upper_body_only"], bool)
        assert isinstance(diag["torso_angle"], float)
        assert isinstance(diag["aspect_ratio"], float)

    def test_upright_standing_posture(self, default_upright_person):
        kpts, confs, bbox = default_upright_person
        feat, diag = extract_biomechanical_features(kpts, confs, bbox)

        assert diag["is_horizontal"] is False
        assert diag["is_upper_body_only"] is False
        assert diag["torso_angle"] >= 70.0
        assert diag["aspect_ratio"] < 1.0  # Tall bounding box (standing)

    def test_seated_webcam_user_no_false_positive_fall(self):
        """Sitting at desk: lower body keypoints obscured, head above shoulders, upright spine."""
        kpts = np.zeros((17, 2), dtype=np.float32)
        kpts[0] = [320, 100]  # nose
        kpts[1] = [315, 95]   # l_eye
        kpts[2] = [325, 95]   # r_eye
        kpts[5] = [260, 220]  # l_shoulder
        kpts[6] = [380, 220]  # r_shoulder
        kpts[7] = [240, 320]  # l_elbow
        kpts[8] = [400, 320]  # r_elbow

        confs = np.zeros(17, dtype=np.float32)
        confs[0] = 0.95
        confs[1] = 0.90
        confs[2] = 0.90
        confs[5] = 0.92
        confs[6] = 0.91
        confs[7] = 0.85
        confs[8] = 0.84

        bbox = np.array([100, 50, 540, 450], dtype=np.int32)
        _, diag = extract_biomechanical_features(kpts, confs, bbox)

        assert diag["is_upper_body_only"] is True
        assert diag["is_horizontal"] is False, "Seated webcam user falsely marked as horizontal fall!"
        assert diag["torso_angle"] >= 45.0

    def test_severe_horizontal_accident_fall(self):
        """Person lying horizontally on road after motorcycle/pedestrian collision."""
        kpts = np.zeros((17, 2), dtype=np.float32)
        kpts[0] = [120, 350]
        kpts[1] = [125, 345]
        kpts[2] = [125, 355]
        kpts[5] = [200, 340]
        kpts[6] = [200, 370]
        kpts[11] = [360, 340]
        kpts[12] = [360, 365]
        kpts[13] = [480, 345]
        kpts[14] = [480, 360]
        kpts[15] = [580, 350]
        kpts[16] = [580, 365]

        confs = np.ones(17, dtype=np.float32) * 0.92
        bbox = np.array([80, 300, 600, 420], dtype=np.int32)

        _, diag = extract_biomechanical_features(kpts, confs, bbox)

        assert diag["is_horizontal"] is True, "Horizontal accident posture NOT detected!"
        assert diag["aspect_ratio"] >= 1.05
        assert diag["torso_angle"] < 38.0

    def test_zero_confidence_all_keypoints(self):
        """Camera obscured / darkness / no person detected."""
        kpts = np.zeros((17, 2), dtype=np.float32)
        confs = np.zeros(17, dtype=np.float32)
        bbox = np.array([0, 0, 100, 100], dtype=np.int32)

        feat, diag = extract_biomechanical_features(kpts, confs, bbox)
        assert feat.shape == (1, 41)
        assert not np.isnan(feat).any()
        assert diag["is_horizontal"] is False

    def test_extreme_zero_size_bounding_box(self):
        """Degenerate zero-pixel bounding box edge case."""
        kpts = np.ones((17, 2), dtype=np.float32) * 50.0
        confs = np.ones(17, dtype=np.float32) * 0.5
        bbox = np.array([50, 50, 50, 50], dtype=np.int32)

        feat, diag = extract_biomechanical_features(kpts, confs, bbox)
        assert feat.shape == (1, 41)
        assert diag["aspect_ratio"] == 1.0
