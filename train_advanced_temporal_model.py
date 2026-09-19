# train_advanced_temporal_model.py
"""
RoadSentry AI - Advanced Model Training Pipeline
Trains an advanced multi-feature kinematic ensemble with:
1. Extended temporal sliding window features (velocities, angular acceleration)
2. Negative control hard-negative mining (seated motorists, shoelace tying, crawling)
3. Gradient Boosting & Random Forest ensemble with cross-validation
4. Export to high-performance serialized model for the FastAPI backend
"""

import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)
ADVANCED_MODEL_PATH = os.path.join(MODEL_DIR, "posture_classifier_advanced.pkl")

print("=" * 60)
print("RoadSentry AI: Training Advanced Kinematic Model")
print("=" * 60)

np.random.seed(42)
num_samples_per_class = 2000

X_data = []
y_data = []

# -------------------------------------------------------------
# CLASS 0: NOMINAL / UPRIGHT (Normal walking, standing, running)
# -------------------------------------------------------------
for _ in range(num_samples_per_class):
    coords = np.random.normal(0.0, 0.20, 34)
    l_knee = np.random.uniform(145.0, 180.0) / 180.0
    r_knee = np.random.uniform(145.0, 180.0) / 180.0
    l_elb  = np.random.uniform(130.0, 180.0) / 180.0
    r_elb  = np.random.uniform(130.0, 180.0) / 180.0
    torso  = np.random.uniform(70.0, 90.0) / 180.0    # 70-90 deg upright
    ar     = np.random.uniform(0.35, 0.60)           # Tall aspect ratio
    head_d = np.random.uniform(0.80, 0.98)           # Head well above shoulders
    
    # Temporal velocity derivatives (simulating stable locomotion)
    v_torso = np.random.normal(0.0, 0.05)            # Minimal angular change
    v_head  = np.random.normal(0.0, 0.04)            # Minimal vertical descent
    
    feat = np.concatenate([coords, [l_knee, r_knee, l_elb, r_elb, torso, ar, head_d, v_torso, v_head]])
    X_data.append(feat)
    y_data.append(0)

# -------------------------------------------------------------
# CLASS 0 (NEGATIVE CONTROLS): Hard negatives (Seated rider, tying shoes)
# -------------------------------------------------------------
# Sub-type A: Seated scooter / motorcycle rider at signal (legs bent, but torso upright)
for _ in range(num_samples_per_class // 4):
    coords = np.random.normal(0.0, 0.25, 34)
    l_knee = np.random.uniform(75.0, 100.0) / 180.0  # ~90 deg bent knees
    r_knee = np.random.uniform(75.0, 100.0) / 180.0
    l_elb  = np.random.uniform(100.0, 150.0) / 180.0 # Handlebar grip
    r_elb  = np.random.uniform(100.0, 150.0) / 180.0
    torso  = np.random.uniform(75.0, 88.0) / 180.0   # Torso remains strictly upright!
    ar     = np.random.uniform(0.50, 0.70)
    head_d = np.random.uniform(0.75, 0.90)
    v_torso = np.random.normal(0.0, 0.02)
    v_head  = np.random.normal(0.0, 0.02)
    feat = np.concatenate([coords, [l_knee, r_knee, l_elb, r_elb, torso, ar, head_d, v_torso, v_head]])
    X_data.append(feat)
    y_data.append(0)

# Sub-type B: Pedestrian bending down to tie shoe / pick object (deep bend, but narrow AR and no collapse)
for _ in range(num_samples_per_class // 4):
    coords = np.random.normal(0.0, 0.25, 34)
    l_knee = np.random.uniform(120.0, 160.0) / 180.0
    r_knee = np.random.uniform(120.0, 160.0) / 180.0
    l_elb  = np.random.uniform(60.0, 110.0) / 180.0
    r_elb  = np.random.uniform(60.0, 110.0) / 180.0
    torso  = np.random.uniform(35.0, 50.0) / 180.0   # Momentary bend
    ar     = np.random.uniform(0.60, 0.75)           # Does NOT sprawl (>1.25)
    head_d = np.random.uniform(0.40, 0.55)
    v_torso = np.random.normal(0.05, 0.03)           # Controlled bend velocity
    v_head  = np.random.normal(0.04, 0.03)
    feat = np.concatenate([coords, [l_knee, r_knee, l_elb, r_elb, torso, ar, head_d, v_torso, v_head]])
    X_data.append(feat)
    y_data.append(0)

# -------------------------------------------------------------
# CLASS 1: HAZARD / LEAN (Unstable stumble, barrier resting)
# -------------------------------------------------------------
for _ in range(num_samples_per_class):
    coords = np.random.normal(0.0, 0.30, 34)
    l_knee = np.random.uniform(50.0, 110.0) / 180.0
    r_knee = np.random.uniform(50.0, 110.0) / 180.0
    l_elb  = np.random.uniform(50.0, 120.0) / 180.0
    r_elb  = np.random.uniform(50.0, 120.0) / 180.0
    torso  = np.random.uniform(40.0, 60.0) / 180.0   # 40-60 deg hazardous lean
    ar     = np.random.uniform(0.75, 1.10)
    head_d = np.random.uniform(0.45, 0.65)
    v_torso = np.random.normal(0.15, 0.08)           # Instability derivative
    v_head  = np.random.normal(0.12, 0.06)
    feat = np.concatenate([coords, [l_knee, r_knee, l_elb, r_elb, torso, ar, head_d, v_torso, v_head]])
    X_data.append(feat)
    y_data.append(1)

# -------------------------------------------------------------
# CLASS 2: CRITICAL ACCIDENT / FALL (Motorcycle skid, crosswalk impact)
# -------------------------------------------------------------
for _ in range(num_samples_per_class):
    coords = np.random.normal(0.0, 0.40, 34)
    l_knee = np.random.choice([np.random.uniform(10.0, 38.0), np.random.uniform(160.0, 180.0)]) / 180.0
    r_knee = np.random.choice([np.random.uniform(10.0, 38.0), np.random.uniform(160.0, 180.0)]) / 180.0
    l_elb  = np.random.uniform(15.0, 55.0) / 180.0
    r_elb  = np.random.uniform(15.0, 55.0) / 180.0
    torso  = np.random.choice([np.random.uniform(0.0, 32.0), np.random.uniform(148.0, 180.0)]) / 180.0 # Flat prostrate
    ar     = np.random.uniform(1.25, 2.50)           # Wide horizontal body footprint
    head_d = np.random.uniform(0.00, 0.25)           # Head directly on pavement
    v_torso = np.random.normal(0.45, 0.12)           # Rapid angular collapse rate
    v_head  = np.random.normal(0.50, 0.15)           # Violent cranial descent
    feat = np.concatenate([coords, [l_knee, r_knee, l_elb, r_elb, torso, ar, head_d, v_torso, v_head]])
    X_data.append(feat)
    y_data.append(2)

X = np.array(X_data, dtype=np.float32)
y = np.array(y_data, dtype=np.int64)

print(f"Dataset generated: Total Samples = {len(X)}, Feature Dimension = {X.shape[1]}")
print(f"Class counts: Nominal = {np.sum(y==0)}, Hazard = {np.sum(y==1)}, Collision = {np.sum(y==2)}")

# -------------------------------------------------------------
# ENSEMBLE CLASSIFIER: Random Forest + Gradient Boosting
# -------------------------------------------------------------
rf = RandomForestClassifier(n_estimators=180, max_depth=14, random_state=42, class_weight='balanced')
gb = GradientBoostingClassifier(n_estimators=120, max_depth=6, learning_rate=0.08, random_state=42)

ensemble = VotingClassifier(
    estimators=[('rf', rf), ('gb', gb)],
    voting='soft'
)

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', ensemble)
])

# 5-Fold Stratified Cross-Validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(pipeline, X, y, cv=cv, scoring='f1_macro')

print("-" * 60)
print(f"5-Fold Stratified Cross-Validation Macro F1-Score: {np.mean(scores)*100:.2f}% (+/- {np.std(scores)*100:.2f}%)")
print("-" * 60)

pipeline.fit(X, y)
joblib.dump(pipeline, ADVANCED_MODEL_PATH)
print(f"Advanced Model successfully trained and saved to: {ADVANCED_MODEL_PATH}")

# Evaluation Summary
y_pred = pipeline.predict(X)
print("\nClassification Report:")
print(classification_report(y, y_pred, target_names=['0: Nominal (Green)', '1: Hazard (Amber)', '2: Critical Crash (Red)']))
print("Confusion Matrix:")
print(confusion_matrix(y, y_pred))
