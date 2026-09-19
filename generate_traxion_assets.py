import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

os.makedirs('paper_assets', exist_ok=True)

# Common styling
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 10,
    'figure.titlesize': 14
})

# =====================================================================
# 1. TRAXION HERO GRAPHIC (Dark Futuristic / Medical CV Aesthetic)
# =====================================================================
def generate_hero_banner():
    fig, ax = plt.subplots(figsize=(16, 6.2), dpi=300)
    fig.patch.set_facecolor('#080b11')
    ax.set_facecolor('#080b11')
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 6.2)
    ax.axis('off')

    # Background subtle grid
    for x in np.arange(0, 16.5, 0.8):
        ax.plot([x, x], [0, 6.2], color='#111827', lw=0.6, alpha=0.6)
    for y in np.arange(0, 6.5, 0.8):
        ax.plot([0, 16], [y, y], color='#111827', lw=0.6, alpha=0.6)

    # Ambient glow patches
    glow_left = patches.Circle((3.2, 3.1), 2.2, facecolor='#06b6d4', alpha=0.06)
    glow_right = patches.Circle((12.5, 3.1), 2.5, facecolor='#8b5cf6', alpha=0.05)
    ax.add_patch(glow_left)
    ax.add_patch(glow_right)

    # Brand Title & Badges (Left / Center-Left)
    badge_bg = patches.FancyBboxPatch((0.8, 5.0), 4.8, 0.55, boxstyle="round,pad=0.1",
                                      facecolor='#0e1726', edgecolor='#06b6d4', lw=1.2)
    ax.add_patch(badge_bg)
    ax.text(3.2, 5.27, "AI-DRIVEN BIOMECHANICAL KINEMATICS", color='#00f0ff',
            fontsize=10.5, fontweight='bold', ha='center', va='center')

    ax.text(0.8, 4.15, "TRAXION", color='#ffffff', fontsize=44, fontweight='heavy',
            ha='left', va='baseline')
    ax.text(6.1, 4.15, "AI", color='#00f0ff', fontsize=44, fontweight='heavy',
            ha='left', va='baseline')

    ax.text(0.8, 3.35, "Real-Time Human Movement & Biomechanical Risk Intelligence",
            color='#94a3b8', fontsize=14, fontweight='medium', ha='left', va='center')
    ax.text(0.8, 2.85, "YOLO11n-Pose  |  17 COCO Keypoints  |  41-D Kinematic Feature Vector  |  Three.js WebGL Twin",
            color='#64748b', fontsize=10.5, ha='left', va='center')

    # Telemetry KPI Chips (Bottom Left)
    kpis = [
        ("INFERENCE", "< 40 ms", "#00f0ff"),
        ("KEYPOINTS", "17 COCO", "#38bdf8"),
        ("FEATURE VECTOR", "41-D BioMech", "#a855f7"),
        ("ACCURACY", "95.2% RF", "#10b981")
    ]
    for i, (lbl, val, col) in enumerate(kpis):
        x_chip = 0.8 + i * 2.2
        chip = patches.FancyBboxPatch((x_chip, 1.2), 2.0, 1.0, boxstyle="round,pad=0.08",
                                     facecolor='#0f172a', edgecolor='#1e293b', lw=1.2)
        ax.add_patch(chip)
        ax.text(x_chip + 1.0, 1.85, lbl, color='#64748b', fontsize=7.5, fontweight='bold', ha='center', va='center')
        ax.text(x_chip + 1.0, 1.5, val, color=col, fontsize=12, fontweight='bold', ha='center', va='center')

    # Biomechanical Skeletal Wireframe (Center-Right, x: 9.8 to 12.2)
    # COCO Keypoints normalized onto canvas
    kpts_canvas = {
        0: (11.0, 4.9),   # Nose
        1: (10.9, 5.0), 2: (11.1, 5.0), # Eyes
        3: (10.75, 4.95), 4: (11.25, 4.95), # Ears
        5: (10.4, 4.1), 6: (11.6, 4.1), # Shoulders
        7: (9.9, 3.3), 8: (12.1, 3.3),  # Elbows
        9: (9.6, 2.5), 10: (12.4, 2.5), # Wrists
        11: (10.6, 2.7), 12: (11.4, 2.7), # Hips
        13: (10.5, 1.7), 14: (11.5, 1.7), # Knees
        15: (10.4, 0.7), 16: (11.6, 0.7)  # Ankles
    }
    bones = [
        (0,1), (0,2), (1,3), (2,4), (5,6), (5,7), (7,9), (6,8), (8,10),
        (5,11), (6,12), (11,12), (11,13), (13,15), (12,14), (14,16)
    ]

    # Draw glow lines for bones
    for b1, b2 in bones:
        p1, p2 = kpts_canvas[b1], kpts_canvas[b2]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#00f0ff', lw=3.0, alpha=0.85, zorder=3)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#06b6d4', lw=6.0, alpha=0.25, zorder=2)

    # Draw joints
    for idx, (jx, jy) in kpts_canvas.items():
        circ_outer = patches.Circle((jx, jy), 0.09, facecolor='#00f0ff', edgecolor='#ffffff', lw=1.2, zorder=4)
        circ_halo = patches.Circle((jx, jy), 0.16, facecolor='#00f0ff', alpha=0.3, zorder=3)
        ax.add_patch(circ_halo)
        ax.add_patch(circ_outer)

    # Joint Labels
    ax.text(11.0, 5.25, "Craniofacial (0:4)", color='#00f0ff', fontsize=8.5, ha='center', va='bottom', fontweight='bold')
    ax.text(9.3, 3.3, "Upper Limbs (5:10)", color='#fbbf24', fontsize=8, ha='right', va='center')
    ax.text(12.7, 2.7, "Spine & Core (11:12)", color='#818cf8', fontsize=8, ha='left', va='center')
    ax.text(12.7, 1.2, "Lower Limbs (13:16)", color='#34d399', fontsize=8, ha='left', va='center')

    # Right HUD Telemetry Card
    hud_card = patches.FancyBboxPatch((13.5, 0.7), 2.2, 4.8, boxstyle="round,pad=0.1",
                                      facecolor='#0d131f', edgecolor='#1e293b', lw=1.4)
    ax.add_patch(hud_card)
    ax.text(14.6, 5.15, "LIVE TELEMETRY", color='#94a3b8', fontsize=8.5, fontweight='bold', ha='center', va='center')
    
    hud_items = [
        ("RISK STATUS", "NOMINAL", "#10b981"),
        ("SPINE INCLINE", "88.4°", "#38bdf8"),
        ("ASPECT RATIO", "0.42", "#a855f7"),
        ("CRANIAL AXIS", "1.74m", "#f59e0b"),
        ("KNEE FLEXION", "172.1°", "#00f0ff"),
        ("PIPELINE FPS", "28.5 FPS", "#34d399")
    ]
    for idx, (title, val, col) in enumerate(hud_items):
        y_pos = 4.5 - idx * 0.65
        ax.text(13.7, y_pos + 0.14, title, color='#64748b', fontsize=7.2, fontweight='bold', ha='left', va='center')
        ax.text(13.7, y_pos - 0.12, val, color=col, fontsize=11, fontweight='bold', ha='left', va='center')

    plt.tight_layout()
    plt.savefig('paper_assets/traxion_hero.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print("✅ Generated: paper_assets/traxion_hero.png")


# =====================================================================
# 2. 17-KEYPOINT ANATOMICAL TOPOLOGY DIAGRAM
# =====================================================================
def generate_17_keypoint_anatomy():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7.5), dpi=300, gridspec_kw={'width_ratios': [1.1, 1]})
    fig.patch.set_facecolor('#0a0d14')
    ax1.set_facecolor('#0a0d14')
    ax2.set_facecolor('#0a0d14')
    ax1.set_xlim(-2.2, 2.2)
    ax1.set_ylim(-2.6, 2.8)
    ax1.axis('off')
    ax2.axis('off')

    # Subtitle / Header on Left
    ax1.text(0, 2.6, "COCO 17-Keypoint Anatomical Coordinate System", color='#ffffff',
             fontsize=14, fontweight='bold', ha='center', va='center')
    ax1.text(0, 2.35, "Scale-Invariant Biomechanical Normalization relative to Root Mid-Hip Origin (x_root, y_root)",
             color='#64748b', fontsize=9.5, ha='center', va='center')

    # Coordinate positions of the 17 keypoints
    kpts = {
        0: (0.0, 1.8),     # Nose
        1: (-0.18, 1.95),  # Left Eye
        2: (0.18, 1.95),   # Right Eye
        3: (-0.35, 1.85),  # Left Ear
        4: (0.35, 1.85),   # Right Ear
        5: (-0.75, 1.25),  # Left Shoulder
        6: (0.75, 1.25),   # Right Shoulder
        7: (-1.15, 0.45),  # Left Elbow
        8: (1.15, 0.45),   # Right Elbow
        9: (-1.45, -0.35), # Left Wrist
        10: (1.45, -0.35), # Right Wrist
        11: (-0.45, 0.0),  # Left Hip
        12: (0.45, 0.0),   # Right Hip
        13: (-0.52, -1.05),# Left Knee
        14: (0.52, -1.05), # Right Knee
        15: (-0.58, -2.15),# Left Ankle
        16: (0.58, -2.15)  # Right Ankle
    }

    bones = [
        (0,1), (0,2), (1,3), (2,4), (5,6), (5,7), (7,9), (6,8), (8,10),
        (5,11), (6,12), (11,12), (11,13), (13,15), (12,14), (14,16)
    ]

    # Draw Root Mid-Hip Axis
    ax1.plot([-0.9, 0.9], [0, 0], color='#8b5cf6', lw=1.2, linestyle='--', alpha=0.6)
    ax1.plot([0, 0], [-2.3, 2.1], color='#8b5cf6', lw=1.2, linestyle='--', alpha=0.3)
    ax1.scatter([0], [0], color='#8b5cf6', s=80, marker='+', zorder=5)
    ax1.text(0.1, -0.15, "Root Origin (x_root, y_root)", color='#a78bfa', fontsize=8, fontweight='bold')

    # Draw Torso Angle Arc
    arc = patches.Arc((0, 0), 1.2, 1.2, angle=0, theta1=0, theta2=90, color='#f59e0b', lw=1.5, linestyle=':')
    ax1.add_patch(arc)
    ax1.text(0.45, 0.45, "θ_torso", color='#f59e0b', fontsize=10, fontweight='bold')

    # Draw Bones
    for b1, b2 in bones:
        p1, p2 = kpts[b1], kpts[b2]
        ax1.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#1e293b', lw=6.0, zorder=1)
        ax1.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#38bdf8', lw=2.4, alpha=0.85, zorder=2)

    # Color grouping for nodes
    groups = {
        'Cranial': ([0, 1, 2, 3, 4], '#00f0ff'),
        'Upper': ([5, 6, 7, 8, 9, 10], '#fbbf24'),
        'Core': ([11, 12], '#818cf8'),
        'Lower': ([13, 14, 15, 16], '#34d399')
    }

    joint_names = [
        "0: Nose", "1: L_Eye", "2: R_Eye", "3: L_Ear", "4: R_Ear",
        "5: L_Shoulder", "6: R_Shoulder", "7: L_Elbow", "8: R_Elbow",
        "9: L_Wrist", "10: R_Wrist", "11: L_Hip", "12: R_Hip",
        "13: L_Knee", "14: R_Knee", "15: L_Ankle", "16: R_Ankle"
    ]

    for gname, (indices, col) in groups.items():
        for idx in indices:
            pt = kpts[idx]
            ax1.scatter([pt[0]], [pt[1]], color=col, s=120, edgecolor='#ffffff', lw=1.5, zorder=4)
            # Offset text
            x_off = 0.14 if pt[0] >= 0 else -0.14
            align = 'left' if pt[0] >= 0 else 'right'
            ax1.text(pt[0] + x_off, pt[1], joint_names[idx], color='#f8fafc',
                     fontsize=8, fontweight='bold', ha=align, va='center', zorder=5)

    # RIGHT AXIS: Structured Keypoint Taxonomy & Normalization Table
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)

    card = patches.FancyBboxPatch((0.2, 0.4), 9.6, 9.2, boxstyle="round,pad=0.15",
                                 facecolor='#0f172a', edgecolor='#1e293b', lw=1.5)
    ax2.add_patch(card)

    ax2.text(5.0, 9.1, "ANATOMICAL TOPOLOGY & NORMALIZATION", color='#00f0ff',
             fontsize=12, fontweight='bold', ha='center', va='center')

    headers = ["ID Range", "Anatomical Group", "Degrees of Freedom", "Diagnostic Focus"]
    for i, h in enumerate(headers):
        x = 0.6 + i * 2.3
        ax2.text(x, 8.4, h, color='#94a3b8', fontsize=8.5, fontweight='bold', ha='left')
    ax2.plot([0.5, 9.5], [8.2, 8.2], color='#334155', lw=1)

    table_data = [
        ("0 - 4", "Craniofacial Axis", "Nose, Eyes, Ears", "Cranial descent, concussion alert"),
        ("5 - 6", "Pectoral Girdle", "Bi-lateral Shoulders", "Shoulder tilt, torso width reference"),
        ("7 - 10", "Upper Extremity", "Elbows & Wrists", "Defense posture, bracing reflex"),
        ("11 - 12", "Pelvic Core", "Bi-lateral Hips", "Center of mass, root normalization"),
        ("13 - 14", "Femoral / Knee", "Left & Right Knees", "Knee flexion angles (θ_knee)"),
        ("15 - 16", "Lower Extremity", "Left & Right Ankles", "Base of support, ground contact")
    ]

    for row_idx, (r1, r2, r3, r4) in enumerate(table_data):
        y = 7.6 - row_idx * 0.75
        col = '#00f0ff' if row_idx == 0 else ('#fbbf24' if row_idx in [1, 2] else ('#818cf8' if row_idx == 3 else '#34d399'))
        ax2.text(0.6, y, r1, color=col, fontsize=8.5, fontweight='bold')
        ax2.text(2.9, y, r2, color='#e2e8f0', fontsize=8.5)
        ax2.text(5.2, y, r3, color='#cbd5e1', fontsize=8)
        ax2.text(7.5, y, r4, color='#94a3b8', fontsize=7.8)

    # Coordinate Normalization Formula Box
    formula_box = patches.FancyBboxPatch((0.6, 0.8), 8.8, 2.4, boxstyle="round,pad=0.1",
                                         facecolor='#1e293b', edgecolor='#334155', lw=1.2)
    ax2.add_patch(formula_box)
    ax2.text(5.0, 2.85, "Scale-Invariant Normalization Formulae", color='#f8fafc',
             fontsize=9.5, fontweight='bold', ha='center')
    ax2.text(5.0, 2.35, r"$\hat{x}_i = \frac{x_i - x_{root}}{H_{bbox}}, \quad \hat{y}_i = \frac{y_i - y_{root}}{H_{bbox}}$",
             color='#38bdf8', fontsize=12, ha='center')
    ax2.text(5.0, 1.7, r"$\theta = \arccos\left(\frac{\vec{v}_1 \cdot \vec{v}_2}{\|\vec{v}_1\| \|\vec{v}_2\|}\right) \times \frac{180}{\pi}$",
             color='#f59e0b', fontsize=11, ha='center')
    ax2.text(5.0, 1.15, "Invariant to subject distance, camera resolution, and digital zoom.",
             color='#94a3b8', fontsize=8, ha='center')

    plt.tight_layout()
    plt.savefig('paper_assets/keypoints_17_anatomy.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print("✅ Generated: paper_assets/keypoints_17_anatomy.png")


# =====================================================================
# 3. 41-D FEATURE VECTOR ARCHITECTURE DIAGRAM
# =====================================================================
def generate_feature_engine_diagram():
    fig, ax = plt.subplots(figsize=(15, 6.8), dpi=300)
    fig.patch.set_facecolor('#080b11')
    ax.set_facecolor('#080b11')
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 6.8)
    ax.axis('off')

    ax.text(7.5, 6.4, "TRAXION 41-DIMENSIONAL BIOMECHANICAL FEATURE VECTOR", color='#ffffff',
            fontsize=14, fontweight='bold', ha='center', va='center')
    ax.text(7.5, 6.05, "Scale-Invariant Anatomical Tensor Architecture Fed to Random Forest Ensemble",
            color='#64748b', fontsize=10, ha='center', va='center')

    # 5 Vector Partition Boxes
    partitions = [
        ("Part 1: Relative Coordinates", "34-D", [
            ("Indices 0 - 33", "17 Joints × (x, y)", "Normalized by BBox Height",
             r"$(\hat{x}_i, \hat{y}_i) = \frac{(x_i - x_{root}, y_i - y_{root})}{H_{bbox}}$")
        ], "#0284c7", 0.6, 3.8),
        ("Part 2: Joint Angles", "4-D", [
            ("Indices 34 - 37", "L/R Knee & Elbow Angles", "3-Point Articulation",
             r"$\theta_{lk}, \theta_{rk}, \theta_{le}, \theta_{re} \in [0.0, 1.0]$")
        ], "#d97706", 4.7, 2.5),
        ("Part 3: Torso Incline", "1-D", [
            ("Index 38", "Spine / Torso Angle", "Angle relative to ground",
             r"$\theta_{torso} = \arctan2(\Delta y, \Delta x) / 180$")
        ], "#8b5cf6", 7.5, 2.2),
        ("Part 4: Aspect Ratio", "1-D", [
            ("Index 39", "Bounding Box Ratio", "Prostration signature",
             r"$AR = W_{bbox} / H_{bbox} \quad (\geq 1.05)$")
        ], "#10b981", 10.0, 2.2),
        ("Part 5: Cranial Depth", "1-D", [
            ("Index 40", "Head Vertical Position", "Head-to-bottom offset",
             r"$D_{cran} = \frac{y_{bottom} - y_{head}}{H_{bbox}}$")
        ], "#ef4444", 12.5, 2.0)
    ]

    for title, dim, items, col, x, w in partitions:
        card = patches.FancyBboxPatch((x, 1.7), w, 3.9, boxstyle="round,pad=0.1",
                                      facecolor='#0f172a', edgecolor=col, lw=1.6)
        ax.add_patch(card)

        # Header Pill
        pill = patches.FancyBboxPatch((x + 0.15, 5.0), w - 0.3, 0.45, boxstyle="round,pad=0.05",
                                      facecolor=col, edgecolor='none')
        ax.add_patch(pill)
        ax.text(x + w/2, 5.22, f"{dim}", color='#ffffff', fontsize=11, fontweight='bold', ha='center', va='center')

        ax.text(x + w/2, 4.65, title, color='#ffffff', fontsize=9.5, fontweight='bold', ha='center', va='center')

        for idx, (l1, l2, l3, l4) in enumerate(items):
            ax.text(x + w/2, 4.2, l1, color='#94a3b8', fontsize=8, fontweight='bold', ha='center')
            ax.text(x + w/2, 3.75, l2, color='#cbd5e1', fontsize=8, ha='center')
            ax.text(x + w/2, 3.3, l3, color='#64748b', fontsize=7.2, ha='center')
            ax.text(x + w/2, 2.4, l4, color=col, fontsize=8.5, ha='center')

    # Bottom Pipeline Flow
    flow_box = patches.FancyBboxPatch((0.6, 0.3), 13.9, 1.1, boxstyle="round,pad=0.08",
                                     facecolor='#111827', edgecolor='#334155', lw=1.2)
    ax.add_patch(flow_box)

    stages = [
        ("Raw YOLO-Pose", "17 Keypoints + Conf"),
        ("Normalization & Math", "Origin & Angles"),
        ("41-D Feature Tensor", "Scale & Pos Invariant"),
        ("Robust Standard Scaler", "Z-Score Transformation"),
        ("Random Forest Ensemble", "100 Trees, MaxDepth=12"),
        ("Risk Output", "LOW / WARNING / CRITICAL")
    ]

    for idx, (s1, s2) in enumerate(stages):
        x_st = 0.8 + idx * 2.3
        ax.text(x_st + 0.9, 0.95, s1, color='#00f0ff' if idx == 2 or idx == 5 else '#e2e8f0',
                fontsize=8.5, fontweight='bold', ha='center', va='center')
        ax.text(x_st + 0.9, 0.65, s2, color='#94a3b8', fontsize=7.2, ha='center', va='center')
        if idx < len(stages) - 1:
            ax.annotate("", xy=(x_st + 2.05, 0.85), xytext=(x_st + 1.8, 0.85),
                        arrowprops=dict(arrowstyle="->", lw=1.5, color='#06b6d4'))

    plt.tight_layout()
    plt.savefig('paper_assets/feature_engine_41d.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print("✅ Generated: paper_assets/feature_engine_41d.png")


# =====================================================================
# 4. REGENERATE FIG1: TRAXION ARCHITECTURAL PIPELINE (No RoadSentry)
# =====================================================================
def generate_traxion_pipeline():
    fig, ax = plt.subplots(figsize=(15, 5.6), dpi=300)
    fig.patch.set_facecolor('#0a0d14')
    ax.set_facecolor('#0a0d14')
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 5.6)
    ax.axis('off')

    arrow_props = dict(arrowstyle="->,head_width=0.35,head_length=0.55", lw=2.0, color="#00f0ff")

    def draw_box(x, y, w, h, title, subtitle, col_border="#00f0ff", bg="#0f172a"):
        p = patches.FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.15", facecolor=bg, edgecolor=col_border, lw=1.6)
        ax.add_patch(p)
        ax.text(x, y + 0.35, title, ha="center", va="center", fontsize=11, fontweight="bold", color="#ffffff")
        ax.text(x, y - 0.25, subtitle, ha="center", va="center", fontsize=8.5, color="#94a3b8")

    draw_box(1.6, 2.8, 2.4, 2.0, "1. Video Ingestion", "Webcam / H.264 MP4\nDecoded In-Memory\nCPU Frame Scaling (640p)", "#0284c7")
    draw_box(4.7, 2.8, 2.6, 2.0, "2. YOLO11n-Pose", "17 Anatomical Joints\nConfidence Filter (c > 0.20)\nWarm JIT Pre-Inference", "#38bdf8")
    draw_box(8.0, 2.8, 2.8, 2.0, "3. Kinematics Engine", "41-D Biomechanical Vector\nTorso Angle θ_torso\nAspect Ratio & Cranial Depth", "#8b5cf6")
    draw_box(11.4, 2.8, 2.7, 2.0, "4. Posture Classifier", "Random Forest (100 Trees)\n95.2% Accuracy, F1=0.95\nUpper-Body Seated Heuristics", "#10b981")

    # Outputs
    draw_box(13.8, 4.3, 2.0, 1.5, "5A. 3D Twin", "Three.js WebGL\nReal-Time Telemetry\nInteractive Orbital Orbit", "#00f0ff")
    draw_box(13.8, 1.3, 2.0, 1.5, "5B. Triage HUD", "Emergency Protocols\nTrauma Zone Mapping\nLow/Warning/Critical", "#ef4444")

    # Arrows
    ax.annotate("", xy=(3.3, 2.8), xytext=(2.9, 2.8), arrowprops=arrow_props)
    ax.annotate("", xy=(6.5, 2.8), xytext=(6.1, 2.8), arrowprops=arrow_props)
    ax.annotate("", xy=(9.9, 2.8), xytext=(9.5, 2.8), arrowprops=arrow_props)
    ax.annotate("", xy=(12.7, 4.3), xytext=(12.4, 3.2), arrowprops=arrow_props)
    ax.annotate("", xy=(12.7, 1.3), xytext=(12.4, 2.4), arrowprops=arrow_props)

    plt.title("Figure 1: End-to-End Traxion Real-Time Biomechanical Movement Intelligence Pipeline",
              fontsize=13, fontweight="bold", pad=14, color="#ffffff")
    plt.tight_layout()
    plt.savefig("paper_assets/fig1_pipeline_large.png", dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print("✅ Regenerated: paper_assets/fig1_pipeline_large.png")


if __name__ == '__main__':
    generate_hero_banner()
    generate_17_keypoint_anatomy()
    generate_feature_engine_diagram()
    generate_traxion_pipeline()
    print("All Traxion assets successfully generated!")
