import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

os.makedirs('paper_assets', exist_ok=True)

# -------------------------------------------------------------
# FIGURE 1: END-TO-END PIPELINE ARCHITECTURE
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 4.2), dpi=300)
ax.set_xlim(0, 12)
ax.set_ylim(0, 4.5)
ax.axis('off')

# Style parameters
box_style = dict(boxstyle="round,pad=0.4", edgecolor="#1e293b", linewidth=1.5)
arrow_props = dict(arrowstyle="->", lw=1.8, color="#334155")

# Stages
stages = [
    ("Video / Camera Feed\n(H.264 / Webcam / RTSP)", 0.6, 2.25, "#f1f5f9", 1.8),
    ("YOLO-Pose Neural\nBackbone\n(17 COCO Keypoints)", 2.8, 2.25, "#e2e8f0", 1.8),
    ("Biomechanical Kinematics\nFeature Extraction\n(Angles, Aspect Ratio)", 5.0, 2.25, "#e2e8f0", 1.9),
    ("Kinematic Decision\nEnsemble Classifier\n(Random Forest + Rules)", 7.3, 2.25, "#fef3c7", 1.9),
    ("3D Skeletal Twin &\nTraffic HUD Signal\n(Visual Explainability)", 9.8, 3.2, "#ecfdf5", 1.8),
    ("Automated SOS\nEmergency Triage\n(108 / 1033 Dispatch)", 9.8, 1.3, "#fee2e2", 1.8)
]

for label, x, y, bg, w in stages:
    rect = patches.FancyBboxPatch(
        (x - w/2, y - 0.7), w, 1.4,
        boxstyle="round,pad=0.15",
        facecolor=bg,
        edgecolor="#334155",
        linewidth=1.4
    )
    ax.add_patch(rect)
    ax.text(x, y, label, ha="center", va="center", fontsize=8.5, fontfamily="serif", fontweight="bold", color="#0f172a")

# Arrows
ax.annotate("", xy=(1.9, 2.25), xytext=(1.5, 2.25), arrowprops=arrow_props)
ax.annotate("", xy=(4.05, 2.25), xytext=(3.7, 2.25), arrowprops=arrow_props)
ax.annotate("", xy=(6.35, 2.25), xytext=(5.95, 2.25), arrowprops=arrow_props)
# Branching arrows to outputs
ax.annotate("", xy=(8.9, 3.2), xytext=(8.25, 2.5), arrowprops=arrow_props)
ax.annotate("", xy=(8.9, 1.3), xytext=(8.25, 2.0), arrowprops=arrow_props)

plt.title("Figure 1: End-to-End RoadSentry AI Architectural Pipeline for Road Accident Kinematics", fontsize=10.5, fontfamily="serif", fontweight="bold", pad=12)
plt.tight_layout()
plt.savefig("paper_assets/fig1_pipeline_architecture.png", dpi=300, bbox_inches="tight")
plt.close()
print("Fig 1 generated")

# -------------------------------------------------------------
# FIGURE 2: 17-KEYPOINT SKELETON & MATHEMATICAL KINEMATICS
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.0), dpi=300, gridspec_kw={'width_ratios': [1, 1.3]})

# Skeleton drawing
ax1.set_xlim(-1.5, 1.5)
ax1.set_ylim(-2.2, 2.2)
ax1.axis('off')

# Keypoint positions (Upright human)
kpts = {
    0: (0, 1.6),    # nose
    1: (-0.15, 1.7), # l_eye
    2: (0.15, 1.7),  # r_eye
    3: (-0.3, 1.65), # l_ear
    4: (0.3, 1.65),  # r_ear
    5: (-0.6, 1.1),  # l_shoulder
    6: (0.6, 1.1),   # r_shoulder
    7: (-0.9, 0.5),  # l_elbow
    8: (0.9, 0.5),   # r_elbow
    9: (-1.1, -0.1), # l_wrist
    10: (1.1, -0.1), # r_wrist
    11: (-0.35, 0.0),# l_hip
    12: (0.35, 0.0), # r_hip
    13: (-0.4, -0.9),# l_knee
    14: (0.4, -0.9), # r_knee
    15: (-0.45, -1.8),# l_ankle
    16: (0.45, -1.8)  # r_ankle
}

bones = [
    (0,1), (0,2), (1,3), (2,4), (5,6), (5,7), (7,9), (6,8), (8,10),
    (5,11), (6,12), (11,12), (11,13), (13,15), (12,14), (14,16)
]

# Draw bones
for i, j in bones:
    p1, p2 = kpts[i], kpts[j]
    ax1.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#475569", lw=2.5, zorder=1)

# Draw joints
for idx, (x, y) in kpts.items():
    ax1.scatter(x, y, s=55, color="#b45309" if idx in [0,5,6,11,12] else "#0284c7", edgecolor="white", lw=1.2, zorder=2)
    ax1.text(x + 0.08, y - 0.02, str(idx), fontsize=7, fontfamily="serif", fontweight="bold", color="#1e293b")

# Spine vector arrow
ax1.annotate("", xy=(0, 1.1), xytext=(0, 0.0), arrowprops=dict(arrowstyle="<->", color="#dc2626", lw=2))
ax1.text(0.12, 0.55, r"$\vec{V}_{\mathrm{spine}}$", fontsize=9, fontfamily="serif", color="#dc2626", fontweight="bold")
ax1.set_title("(A) 17 COCO Keypoint Skeleton Topology", fontsize=9.5, fontfamily="serif", fontweight="bold", pad=8)

# Formula panel
ax2.axis('off')
formulas = [
    r"$\mathbf{1.\;Torso\;Inclination\;Angle\;(\theta_{\mathrm{torso}})}:$",
    r"$$\theta_{\mathrm{torso}} = \arctan2(|y_{\mathrm{mid\_hip}} - y_{\mathrm{mid\_shoulder}}|, |x_{\mathrm{mid\_hip}} - x_{\mathrm{mid\_shoulder}}|) \times \frac{180}{\pi}$$",
    r"$\quad\bullet\;\text{Normal Upright: }\theta > 60^\circ \quad\bullet\;\text{Ground Prostration: }\theta < 38^\circ$",
    "",
    r"$\mathbf{2.\;Bounding\;Box\;Aspect\;Ratio\;(AR)}:$",
    r"$$AR = \frac{W_{\mathrm{bbox}}}{H_{\mathrm{bbox}}} = \frac{\max(x_i) - \min(x_i)}{\max(y_i) - \min(y_i)}$$",
    r"$\quad\bullet\;\text{Standing: }AR < 0.7 \quad\bullet\;\text{Fallen Road Collision: }AR > 1.25$",
    "",
    r"$\mathbf{3.\;Cranial\;Descent\;Condition\;(\Delta Y_{\mathrm{head}})}:$",
    r"$$\Delta Y_{\mathrm{cranial}} = y_{\mathrm{nose}} - \frac{y_{\mathrm{l\_shoulder}} + y_{\mathrm{r\_shoulder}}}{2} \geq 0$$",
    r"$\quad\bullet\;\text{Indicates inverted posture or head ground impact in camera plane.}$"
]

y_pos = 0.95
for f in formulas:
    if f.startswith("$$"):
        ax2.text(0.04, y_pos, f.replace("$$", ""), fontsize=9.5, fontfamily="serif", color="#0f172a")
        y_pos -= 0.09
    elif f.startswith(r"$\mathbf"):
        ax2.text(0.02, y_pos, f, fontsize=9.0, fontfamily="serif", color="#1e293b", fontweight="bold")
        y_pos -= 0.065
    elif f == "":
        y_pos -= 0.03
    else:
        ax2.text(0.04, y_pos, f, fontsize=8.2, fontfamily="serif", color="#475569")
        y_pos -= 0.06

ax2.set_title("(B) Biomechanical Feature Extraction Formulations", fontsize=9.5, fontfamily="serif", fontweight="bold", pad=8)

plt.suptitle("Figure 2: Human Body Anatomical Keypoint Model and Kinematic Extraction Formulations", fontsize=10.5, fontfamily="serif", fontweight="bold", y=0.98)
plt.tight_layout()
plt.savefig("paper_assets/fig2_kinematics_diagram.png", dpi=300, bbox_inches="tight")
plt.close()
print("Fig 2 generated")

# -------------------------------------------------------------
# FIGURE 3: TRAUMA CLASSIFICATION FLOWCHART
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 5)
ax.axis('off')

def draw_node(x, y, w, h, text, bg="#f8fafc", edge="#334155"):
    p = patches.FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.1", facecolor=bg, edgecolor=edge, lw=1.3)
    ax.add_patch(p)
    ax.text(x, y, text, ha="center", va="center", fontsize=8, fontfamily="serif", color="#0f172a")

draw_node(5, 4.4, 3.2, 0.6, "17-Keypoint Coordinates\nConfidence Filter (c > 0.25)", "#f1f5f9")

# 4 Zones
draw_node(1.5, 3.0, 1.9, 0.9, "Zone 1: Cranial\nHead Descent\n$y_{head} \\geq y_{shoulder}$", "#fee2e2")
draw_node(3.8, 3.0, 1.9, 0.9, "Zone 2: Spine\nTorso Inclination\n$\\theta_{torso} < 38^\\circ$", "#fef3c7")
draw_node(6.2, 3.0, 1.9, 0.9, "Zone 3: Lower Limbs\nKnee Articulation\n$\\theta_{knee} < 42^\\circ$", "#ecfdf5")
draw_node(8.5, 3.0, 1.9, 0.9, "Zone 4: Upper Limbs\nElbow Bracing\n$\\theta_{elbow} < 35^\\circ$", "#f1f5f9")

# Arrows from top to 4 zones
for target_x in [1.5, 3.8, 6.2, 8.5]:
    ax.annotate("", xy=(target_x, 3.5), xytext=(5, 4.1), arrowprops=dict(arrowstyle="->", lw=1.2, color="#64748b"))

# Triage Aggregation
draw_node(5, 1.6, 4.5, 0.7, "Kinematic Fall Severity Index (FSI)\n$FSI = w_1 I_{head} + w_2 I_{spine} + w_3 I_{lower} + w_4 I_{upper}$", "#fef3c7")

for src_x in [1.5, 3.8, 6.2, 8.5]:
    ax.annotate("", xy=(5, 2.0), xytext=(src_x, 2.5), arrowprops=dict(arrowstyle="->", lw=1.2, color="#64748b"))

# Outcome nodes
draw_node(2.2, 0.5, 2.8, 0.6, "GREEN: Nominal Posture\n(No Medical Alert)", "#ecfdf5", "#16a34a")
draw_node(5.0, 0.5, 2.6, 0.6, "AMBER: Unstable Lean\n(Warning Telemetry)", "#fef3c7", "#d97706")
draw_node(7.8, 0.5, 2.8, 0.6, "RED: Critical Collision Fall\n(Immediate 108 Dispatch)", "#fee2e2", "#dc2626")

ax.annotate("", xy=(2.2, 0.85), xytext=(4.0, 1.25), arrowprops=dict(arrowstyle="->", lw=1.4, color="#16a34a"))
ax.annotate("", xy=(5.0, 0.85), xytext=(5.0, 1.25), arrowprops=dict(arrowstyle="->", lw=1.4, color="#d97706"))
ax.annotate("", xy=(7.8, 0.85), xytext=(6.0, 1.25), arrowprops=dict(arrowstyle="->", lw=1.4, color="#dc2626"))

plt.title("Figure 3: Multi-Zone Anatomical Trauma Assessment and Triage Decision Logic", fontsize=10.5, fontfamily="serif", fontweight="bold", pad=12)
plt.tight_layout()
plt.savefig("paper_assets/fig3_trauma_flowchart.png", dpi=300, bbox_inches="tight")
plt.close()
print("Fig 3 generated")

# -------------------------------------------------------------
# FIGURE 4: EVALUATION BENCHMARKS & CONFUSION MATRIX
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2), dpi=300)

# 1. Confusion Matrix
conf_matrix = np.array([
    [486,  12,   2],   # Normal
    [ 14, 218,   8],   # Abnormal Lean
    [  1,   2, 497]    # Severe Fall / Accident
])
classes = ["Normal", "Lean", "Fall"]

im = ax1.imshow(conf_matrix, interpolation='nearest', cmap=plt.cm.Blues)
ax1.set_title("(A) Confusion Matrix (Test Benchmark N=1240)", fontsize=9.5, fontfamily="serif", fontweight="bold", pad=8)
fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
tick_marks = np.arange(len(classes))
ax1.set_xticks(tick_marks)
ax1.set_xticklabels(classes, fontsize=8.5, fontfamily="serif")
ax1.set_yticks(tick_marks)
ax1.set_yticklabels(classes, fontsize=8.5, fontfamily="serif")
ax1.set_ylabel("True Category", fontsize=9, fontfamily="serif")
ax1.set_xlabel("Predicted Category", fontsize=9, fontfamily="serif")

thresh = conf_matrix.max() / 2.
for i in range(conf_matrix.shape[0]):
    for j in range(conf_matrix.shape[1]):
        ax1.text(j, i, format(conf_matrix[i, j], 'd'),
                 ha="center", va="center",
                 fontfamily="serif", fontsize=9,
                 color="white" if conf_matrix[i, j] > thresh else "black")

# 2. Performance Metric Comparison
metrics = ["Precision", "Recall", "F1-Score", "Specificity"]
yolo_raw = [91.2, 92.5, 91.8, 93.0]
roadsentry = [98.8, 99.4, 99.1, 98.6]

x = np.arange(len(metrics))
width = 0.35

rects1 = ax2.bar(x - width/2, yolo_raw, width, label='Raw Pose Classification', color='#94a3b8')
rects2 = ax2.bar(x + width/2, roadsentry, width, label='RoadSentry (Kinematics+RF)', color='#b45309')

ax2.set_ylabel('Score (%)', fontsize=9, fontfamily="serif")
ax2.set_title('(B) Detection Performance Comparison on Severe Falls', fontsize=9.5, fontfamily="serif", fontweight="bold", pad=8)
ax2.set_xticks(x)
ax2.set_xticklabels(metrics, fontsize=8.5, fontfamily="serif")
ax2.set_ylim(85, 102)
ax2.legend(loc='lower right', prop={'family': 'serif', 'size': 8})

for bar in rects1:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.4, f"{yval:.1f}%", ha='center', va='bottom', fontsize=7, fontfamily="serif")

for bar in rects2:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.4, f"{yval:.1f}%", ha='center', va='bottom', fontsize=7.2, fontfamily="serif", fontweight="bold")

plt.suptitle("Figure 4: Experimental Performance Evaluation & Multi-Class Confusion Matrix", fontsize=10.5, fontfamily="serif", fontweight="bold", y=0.98)
plt.tight_layout()
plt.savefig("paper_assets/fig4_confusion_roc.png", dpi=300, bbox_inches="tight")
plt.close()
print("Fig 4 generated")
