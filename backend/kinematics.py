import numpy as np

KEYPOINTS_MAP = {
    'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4,
    'left_shoulder': 5, 'right_shoulder': 6,
    'left_elbow': 7, 'right_elbow': 8,
    'left_wrist': 9, 'right_wrist': 10,
    'left_hip': 11, 'right_hip': 12,
    'left_knee': 13, 'right_knee': 14,
    'left_ankle': 15, 'right_ankle': 16
}

def calculate_angle(p1, p2, p3):
    """Calculates interior angle at p2 formed by (p1 - p2 - p3) in degrees."""
    v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
    v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    if norm == 0:
        return 90.0
    dot = np.dot(v1, v2)
    return float(np.degrees(np.arccos(np.clip(dot / norm, -1.0, 1.0))))

def extract_biomechanical_features(kpts, confs, bbox):
    """
    Extracts a scale-invariant 41-dimensional feature vector:
    - 34 normalized relative coordinates (relative to root origin)
    - 4 anatomical limb angles (knees, elbows)
    - 1 torso inclination angle relative to ground
    - 1 bounding box aspect ratio
    - 1 relative vertical depth (head-to-ground offset)
    """
    bx1, by1, bx2, by2 = bbox
    bw = max(1.0, float(bx2 - bx1))
    bh = max(1.0, float(by2 - by1))
    aspect_ratio = float(bw / bh)

    has_l_sh = bool(confs[5] > 0.20)
    has_r_sh = bool(confs[6] > 0.20)
    has_l_hip = bool(confs[11] > 0.20)
    has_r_hip = bool(confs[12] > 0.20)
    has_head = bool(confs[0] > 0.20 or confs[1] > 0.20 or confs[2] > 0.20)

    # Calculate mid-shoulder point
    if has_l_sh and has_r_sh:
        mid_sh_x = (kpts[5][0] + kpts[6][0]) / 2.0
        mid_sh_y = (kpts[5][1] + kpts[6][1]) / 2.0
    elif has_l_sh:
        mid_sh_x, mid_sh_y = kpts[5][0], kpts[5][1]
    elif has_r_sh:
        mid_sh_x, mid_sh_y = kpts[6][0], kpts[6][1]
    else:
        mid_sh_x, mid_sh_y = (bx1 + bx2) / 2.0, by1 + bh * 0.25

    # Calculate mid-hip point
    has_hips = has_l_hip or has_r_hip
    if has_l_hip and has_r_hip:
        root_x = (kpts[11][0] + kpts[12][0]) / 2.0
        root_y = (kpts[11][1] + kpts[12][1]) / 2.0
    elif has_l_hip:
        root_x, root_y = kpts[11][0], kpts[11][1]
    elif has_r_hip:
        root_x, root_y = kpts[12][0], kpts[12][1]
    else:
        # Fallback: estimate hip position below shoulders
        root_x = mid_sh_x
        root_y = mid_sh_y + bh * 0.45

    # 1. Normalized Relative Coordinates
    norm_coords = []
    for (x, y), c in zip(kpts, confs):
        if c > 0.10:
            norm_coords.extend([(x - root_x) / bh, (y - root_y) / bh])
        else:
            norm_coords.extend([0.0, 0.0])

    # 2. Joint Angles
    l_knee_ang = calculate_angle(kpts[11], kpts[13], kpts[15]) if min(confs[11], confs[13], confs[15]) > 0.15 else 90.0
    r_knee_ang = calculate_angle(kpts[12], kpts[14], kpts[16]) if min(confs[12], confs[14], confs[16]) > 0.15 else 90.0
    l_elb_ang = calculate_angle(kpts[5], kpts[7], kpts[9]) if min(confs[5], confs[7], confs[9]) > 0.15 else 90.0
    r_elb_ang = calculate_angle(kpts[6], kpts[8], kpts[10]) if min(confs[6], confs[8], confs[10]) > 0.15 else 90.0

    # 3. Torso Incline Angle & Orientation Analysis
    if has_hips and (has_l_sh or has_r_sh):
        # We have actual spine line (shoulders to hips)
        torso_dy = root_y - mid_sh_y  # positive if hips are below shoulders
        torso_dx = root_x - mid_sh_x
        # Angle of spine relative to horizontal plane
        torso_ang = abs(float(np.degrees(np.arctan2(abs(torso_dy), abs(torso_dx)))))
    elif has_head and (has_l_sh or has_r_sh):
        # Upper body only (e.g. webcam sitting at desk)
        # Head-to-shoulder vector: should be vertical (head above shoulders)
        head_x = kpts[0][0] if confs[0] > 0.20 else (kpts[1][0] if confs[1] > 0.20 else kpts[2][0])
        head_y = kpts[0][1] if confs[0] > 0.20 else (kpts[1][1] if confs[1] > 0.20 else kpts[2][1])
        neck_dy = mid_sh_y - head_y  # positive if shoulders are below head
        neck_dx = mid_sh_x - head_x
        torso_ang = abs(float(np.degrees(np.arctan2(abs(neck_dy), abs(neck_dx)))))
    else:
        torso_ang = 90.0

    # 4. Vertical Offsets
    head_y = min(kpts[0][1], kpts[1][1], kpts[2][1])
    head_to_bottom = float((by2 - head_y) / bh)

    # 5. Robust Fall / Horizontal Prostration Detection
    # Avoid FALSE POSITIVES for seated webcam users!
    is_upper_body_only = not (has_l_hip and has_r_hip and (confs[13] > 0.15 or confs[14] > 0.15))
    
    is_head_above_shoulders = bool(has_head and (head_y < mid_sh_y - 15))

    if is_upper_body_only:
        # For a seated or upper-body webcam view:
        # As long as the head is above the shoulders and neck is reasonably upright,
        # it is NEVER a horizontal accident prostration!
        if is_head_above_shoulders and torso_ang >= 45.0:
            is_horizontal = False
        elif not is_head_above_shoulders and torso_ang < 35.0:
            # Head has collapsed below or level with shoulders
            is_horizontal = True
        else:
            is_horizontal = False
    else:
        # Full body in view:
        # A true fall has spine angle < 38 degrees with horizontal AND wide aspect ratio
        is_horizontal = bool(torso_ang < 38.0 and aspect_ratio >= 1.05 and (head_y > by1 + bh * 0.3))

    extra_features = [
        float(l_knee_ang / 180.0), float(r_knee_ang / 180.0),
        float(l_elb_ang / 180.0), float(r_elb_ang / 180.0),
        float(torso_ang / 180.0), aspect_ratio, head_to_bottom
    ]

    feature_vector = np.array(norm_coords + extra_features, dtype=np.float32).reshape(1, -1)

    diagnostic_data = {
        "torso_angle": float(round(torso_ang, 1)),
        "aspect_ratio": float(round(aspect_ratio, 2)),
        "left_knee_angle": float(round(float(l_knee_ang), 1)),
        "right_knee_angle": float(round(float(r_knee_ang), 1)),
        "left_elbow_angle": float(round(float(l_elb_ang), 1)),
        "right_elbow_angle": float(round(float(r_elb_ang), 1)),
        "is_upper_body_only": bool(is_upper_body_only),
        "is_horizontal": bool(is_horizontal)
    }

    return feature_vector, diagnostic_data
