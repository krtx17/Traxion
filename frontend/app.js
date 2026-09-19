// ===================================================================
// TRAXION AI - Intelligent Road Accident & Fall Kinematics Client
// ===================================================================

const AppState = {
  currentMode: 'camera', // 'camera' or 'video'
  
  // Camera State
  isCameraActive: false,
  mediaStream: null,
  inferenceInterval: null,
  
  // Recording State
  mediaRecorder: null,
  recordedChunks: [],
  isRecording: false,
  recordingTimerInterval: null,
  recordingSeconds: 0,
  recordedVideoBlob: null,
  
  // Telemetry & FPS
  fpsCounter: 0,
  lastFpsTimestamp: performance.now(),
  currentFps: 0
};

// COCO Skeleton Connections for Canvas Rendering
const COCO_PAIRS = [
  [0, 1], [0, 2], [1, 3], [2, 4],           // Head
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],   // Arms
  [5, 11], [6, 12], [11, 12],                // Torso
  [11, 13], [13, 15], [12, 14], [14, 16]     // Legs
];

// -------------------------------------------------------------
// 1. THREE.JS 3D SKELETAL BODY MODEL
// -------------------------------------------------------------
let scene3D, camera3D, renderer3D, bodyGroup;
const bodyLimbs = {};

function init3DBodyModel() {
  const container = document.getElementById("skeleton3dContainer");
  if (!container || !window.THREE) return;

  const w = container.clientWidth || 320;
  const h = container.clientHeight || 360;

  scene3D = new THREE.Scene();
  scene3D.background = new THREE.Color(0x0e1117);

  camera3D = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
  camera3D.position.set(0, 0.2, 6.8);

  renderer3D = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer3D.setSize(w, h);
  renderer3D.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.innerHTML = "";
  container.appendChild(renderer3D.domElement);

  // Lights
  const ambLight = new THREE.AmbientLight(0xffffff, 0.9);
  scene3D.add(ambLight);

  const keyLight = new THREE.PointLight(0xffeedd, 1.6, 30);
  keyLight.position.set(3, 5, 5);
  scene3D.add(keyLight);

  const rimLight = new THREE.PointLight(0x94a3b8, 1.0, 30);
  rimLight.position.set(-3, -3, 4);
  scene3D.add(rimLight);

  // Grid floor
  const grid = new THREE.GridHelper(6, 14, 0x334155, 0x1e293b);
  grid.position.y = -2.5;
  scene3D.add(grid);

  bodyGroup = new THREE.Group();

  const baseMaterial = new THREE.MeshStandardMaterial({
    color: 0xcfd8dc,
    emissive: 0x1e2530,
    roughness: 0.3,
    metalness: 0.6,
    wireframe: true
  });

  function addNode(r, x, y, z, name) {
    const geo = new THREE.SphereGeometry(r, 14, 14);
    const mesh = new THREE.Mesh(geo, baseMaterial.clone());
    mesh.position.set(x, y, z);
    bodyGroup.add(mesh);
    bodyLimbs[name] = mesh;
    return mesh;
  }

  function addLimb(r, len, x, y, z, rx, rz, name) {
    const geo = new THREE.CylinderGeometry(r, r, len, 10);
    const mesh = new THREE.Mesh(geo, baseMaterial.clone());
    mesh.position.set(x, y, z);
    mesh.rotation.x = rx;
    mesh.rotation.z = rz;
    bodyGroup.add(mesh);
    bodyLimbs[name] = mesh;
    return mesh;
  }

  // Anatomical Human Nodes
  addNode(0.36, 0, 1.75, 0, "head");
  addLimb(0.18, 1.1, 0, 0.7, 0, 0, 0, "spine");
  addNode(0.30, 0, 0.05, 0, "pelvis");

  // Left Arm
  addNode(0.15, -0.65, 1.2, 0, "l_shoulder");
  addLimb(0.10, 0.65, -0.88, 0.78, 0, 0, 0.25, "l_upper_arm");
  addNode(0.12, -1.1, 0.35, 0, "l_elbow");
  addLimb(0.08, 0.55, -1.25, -0.05, 0, 0, 0.18, "l_forearm");

  // Right Arm
  addNode(0.15, 0.65, 1.2, 0, "r_shoulder");
  addLimb(0.10, 0.65, 0.88, 0.78, 0, 0, -0.25, "r_upper_arm");
  addNode(0.12, 1.1, 0.35, 0, "r_elbow");
  addLimb(0.08, 0.55, 1.25, -0.05, 0, 0, -0.18, "r_forearm");

  // Left Leg
  addNode(0.15, -0.38, -0.15, 0, "l_hip");
  addLimb(0.13, 0.9, -0.42, -0.75, 0, 0, 0.04, "l_thigh");
  addNode(0.13, -0.46, -1.35, 0, "l_knee");
  addLimb(0.10, 0.9, -0.48, -1.95, 0, 0, 0.02, "l_shin");

  // Right Leg
  addNode(0.15, 0.38, -0.15, 0, "r_hip");
  addLimb(0.13, 0.9, 0.42, -0.75, 0, 0, -0.04, "r_thigh");
  addNode(0.13, 0.46, -1.35, 0, "r_knee");
  addLimb(0.10, 0.9, 0.48, -1.95, 0, 0, -0.02, "r_shin");

  bodyGroup.position.y = 0.3;
  scene3D.add(bodyGroup);

  // Interactive Drag Controls
  let isDragging = false;
  let prevMouseX = 0;

  container.addEventListener("mousedown", (e) => {
    isDragging = true;
    prevMouseX = e.clientX;
  });
  window.addEventListener("mousemove", (e) => {
    if (isDragging && bodyGroup) {
      bodyGroup.rotation.y += (e.clientX - prevMouseX) * 0.015;
      prevMouseX = e.clientX;
    }
  });
  window.addEventListener("mouseup", () => { isDragging = false; });

  // Touch controls
  container.addEventListener("touchstart", (e) => {
    isDragging = true;
    prevMouseX = e.touches[0].clientX;
  });
  window.addEventListener("touchmove", (e) => {
    if (isDragging && bodyGroup) {
      bodyGroup.rotation.y += (e.touches[0].clientX - prevMouseX) * 0.015;
      prevMouseX = e.touches[0].clientX;
    }
  });
  window.addEventListener("touchend", () => { isDragging = false; });

  // Render Loop
  function renderLoop() {
    requestAnimationFrame(renderLoop);
    if (!isDragging && bodyGroup) {
      bodyGroup.rotation.y += 0.005; // Gentle rotation
    }
    renderer3D.render(scene3D, camera3D);
  }
  renderLoop();

  window.addEventListener("resize", () => {
    if (!container || !camera3D || !renderer3D) return;
    const nw = container.clientWidth;
    const nh = container.clientHeight;
    if (nw > 0 && nh > 0) {
      camera3D.aspect = nw / nh;
      camera3D.updateProjectionMatrix();
      renderer3D.setSize(nw, nh);
    }
  });
}

function update3DTraumaHighlights(impactedZones = []) {
  const normalColor = new THREE.Color(0xcfd8dc); // Neutral Titanium
  const alertColor = new THREE.Color(0xdc2626);  // Deep Red
  const warnColor = new THREE.Color(0xd97706);   // Road Amber

  // Reset to Normal Titanium
  Object.values(bodyLimbs).forEach(m => {
    m.material.color.copy(normalColor);
    m.material.emissive.setHex(0x1e2530);
  });

  const hasHead = impactedZones.some(z => z.includes("Head"));
  const hasSpine = impactedZones.some(z => z.includes("Spine"));
  const hasUpper = impactedZones.some(z => z.includes("Upper"));
  const hasLower = impactedZones.some(z => z.includes("Lower"));

  // Update Zone HTML Badges
  updateZonePill("zoneHead", "zoneHeadText", hasHead);
  updateZonePill("zoneSpine", "zoneSpineText", hasSpine);
  updateZonePill("zoneUpper", "zoneUpperText", hasUpper);
  updateZonePill("zoneLower", "zoneLowerText", hasLower);

  if (hasHead && bodyLimbs["head"]) {
    bodyLimbs["head"].material.color.copy(alertColor);
    bodyLimbs["head"].material.emissive.setHex(0x880011);
  }

  if (hasSpine) {
    ["spine", "pelvis"].forEach(k => {
      if (bodyLimbs[k]) {
        bodyLimbs[k].material.color.copy(alertColor);
        bodyLimbs[k].material.emissive.setHex(0x880011);
      }
    });
  }

  if (hasUpper) {
    ["l_shoulder", "l_upper_arm", "l_elbow", "l_forearm", "r_shoulder", "r_upper_arm", "r_elbow", "r_forearm"].forEach(k => {
      if (bodyLimbs[k]) {
        bodyLimbs[k].material.color.copy(warnColor);
        bodyLimbs[k].material.emissive.setHex(0x553300);
      }
    });
  }

  if (hasLower) {
    ["l_hip", "l_thigh", "l_knee", "l_shin", "r_hip", "r_thigh", "r_knee", "r_shin"].forEach(k => {
      if (bodyLimbs[k]) {
        bodyLimbs[k].material.color.copy(alertColor);
        bodyLimbs[k].material.emissive.setHex(0x880011);
      }
    });
  }
}

function updateZonePill(pillId, textId, isAlert) {
  const pill = document.getElementById(pillId);
  const text = document.getElementById(textId);
  if (!pill || !text) return;

  if (isAlert) {
    pill.className = "p-1.5 rounded bg-red-950/40 border border-red-800 transition-all";
    text.className = "text-red-400 font-bold text-xs";
    text.textContent = "IMPACT";
  } else {
    pill.className = "p-1.5 rounded bg-void border border-border transition-all";
    text.className = "text-emerald-400 font-bold text-xs";
    text.textContent = "NORMAL";
  }
}

// -------------------------------------------------------------
// 2. MODE SWITCHER (CAMERA vs VIDEO)
// -------------------------------------------------------------
function switchMode(mode) {
  AppState.currentMode = mode;
  const btnCam = document.getElementById("modeBtnCamera");
  const btnVid = document.getElementById("modeBtnVideo");
  const viewCam = document.getElementById("viewModeCamera");
  const viewVid = document.getElementById("viewModeVideo");

  if (mode === "camera") {
    viewCam.classList.remove("hidden");
    viewVid.classList.add("hidden");

    btnCam.className = "px-3 py-1 rounded bg-amber-900/30 text-amber-300 font-bold border border-amber-800/50 transition-all";
    btnVid.className = "px-3 py-1 rounded text-slate-400 hover:text-white transition-all";
  } else {
    viewCam.classList.add("hidden");
    viewVid.classList.remove("hidden");

    btnVid.className = "px-3 py-1 rounded bg-amber-900/30 text-amber-300 font-bold border border-amber-800/50 transition-all";
    btnCam.className = "px-3 py-1 rounded text-slate-400 hover:text-white transition-all";

    // Pause live webcam if active
    if (AppState.isCameraActive) {
      toggleWebcam(false);
    }
  }

  lucide.createIcons();
}

// -------------------------------------------------------------
// 3. LIVE CAMERA DETECTION & SKELETON HUD
// -------------------------------------------------------------
async function toggleWebcam(forceState) {
  const targetState = forceState !== undefined ? forceState : !AppState.isCameraActive;
  const toggleBtnText = document.getElementById("toggleCamText");
  const liveIndicator = document.getElementById("liveIndicatorDot");
  const placeholder = document.getElementById("cameraPlaceholder");
  const recordBtn = document.getElementById("recordBtn");
  const snapBtn = document.getElementById("snapBtn");
  const videoEl = document.getElementById("webcamVideo");
  const canvas = document.getElementById("cameraCanvas");

  if (targetState) {
    // START CAMERA
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      });

      AppState.mediaStream = stream;
      AppState.isCameraActive = true;

      if (videoEl) {
        videoEl.srcObject = stream;
        await videoEl.play();
      }

      if (toggleBtnText) toggleBtnText.textContent = "Stop Camera";
      if (liveIndicator) liveIndicator.className = "w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse";
      if (placeholder) placeholder.classList.add("hidden");

      // Enable Record & Snapshot
      if (recordBtn) {
        recordBtn.disabled = false;
        recordBtn.className = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface text-slate-300 hover:text-white border border-border text-xs font-mono transition-all cursor-pointer";
      }
      if (snapBtn) snapBtn.disabled = false;

      startLiveInferenceStream();

    } catch (err) {
      console.error("Webcam access error:", err);
      alert(`Could not start webcam: ${err.message}`);
      AppState.isCameraActive = false;
      if (toggleBtnText) toggleBtnText.textContent = "Start Camera";
      if (liveIndicator) liveIndicator.className = "w-2.5 h-2.5 rounded-full bg-slate-600";
    }

  } else {
    // STOP CAMERA
    AppState.isCameraActive = false;

    if (AppState.inferenceInterval) {
      clearInterval(AppState.inferenceInterval);
      AppState.inferenceInterval = null;
    }

    if (AppState.isRecording) {
      toggleRecording(false);
    }

    if (AppState.mediaStream) {
      AppState.mediaStream.getTracks().forEach(t => t.stop());
      AppState.mediaStream = null;
    }

    if (toggleBtnText) toggleBtnText.textContent = "Start Camera";
    if (liveIndicator) liveIndicator.className = "w-2.5 h-2.5 rounded-full bg-slate-600";
    if (placeholder) placeholder.classList.remove("hidden");

    if (recordBtn) {
      recordBtn.disabled = true;
      recordBtn.className = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 text-slate-500 border border-border text-xs font-mono transition-all cursor-not-allowed";
    }
    if (snapBtn) snapBtn.disabled = true;

    // Reset telemetry
    updateTelemetryCard({ posture: "STANDBY", risk_level: "LOW", torso_angle: null });
    update3DTraumaHighlights([]);

    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }

  lucide.createIcons();
}

function startLiveInferenceStream() {
  const videoEl = document.getElementById("webcamVideo");
  const canvas = document.getElementById("cameraCanvas");
  if (!videoEl || !canvas) return;

  const ctx = canvas.getContext("2d");
  let isSendingFrame = false;

  // Offscreen canvas for fast downscaled JPEG encoding
  const offscreen = document.createElement("canvas");
  offscreen.width = 384;
  offscreen.height = 288;
  const offCtx = offscreen.getContext("2d");

  AppState.inferenceInterval = setInterval(async () => {
    if (!AppState.isCameraActive || isSendingFrame || videoEl.readyState < 2) return;

    canvas.width = videoEl.videoWidth || 640;
    canvas.height = videoEl.videoHeight || 480;

    // 1. Draw raw video frame to display canvas
    ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

    // 2. Downscale frame for ultra-fast network inference
    offCtx.drawImage(videoEl, 0, 0, offscreen.width, offscreen.height);
    const frameData = offscreen.toDataURL("image/jpeg", 0.65);

    isSendingFrame = true;

    try {
      const res = await fetch("/api/detect/frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: frameData })
      });

      if (res.ok) {
        const data = await res.json();
        
        // 3. Render 17-Keypoint HUD overlay directly onto live canvas
        drawSkeletonHUD(ctx, data, canvas.width, canvas.height);
        
        // 4. Update Telemetry & 3D Model
        updateTelemetryCard(data);
        update3DTraumaHighlights(data.impacted_zones || []);

        // Compute Live FPS
        AppState.fpsCounter++;
        const now = performance.now();
        if (now - AppState.lastFpsTimestamp >= 1000) {
          AppState.currentFps = Math.round((AppState.fpsCounter * 1000) / (now - AppState.lastFpsTimestamp));
          AppState.fpsCounter = 0;
          AppState.lastFpsTimestamp = now;
          const fpsEl = document.getElementById("liveFpsText");
          if (fpsEl) fpsEl.textContent = `${AppState.currentFps} FPS`;
        }
      }
    } catch (e) {
      console.warn("Live stream frame error:", e);
    } finally {
      isSendingFrame = false;
    }
  }, 95); // ~10-12 FPS real-time
}

function drawSkeletonHUD(ctx, data, w, h) {
  if (!data || !data.keypoints || data.keypoints.length === 0) return;

  const keypoints = data.keypoints;
  const isAccident = data.risk_level === "CRITICAL";
  const lineColor = isAccident ? "#dc2626" : "#d97706";
  const jointColor = isAccident ? "#b91c1c" : "#f59e0b";

  const scaleX = w / 384;
  const scaleY = h / 288;

  // Draw Skeleton Bones
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = lineColor;
  COCO_PAIRS.forEach(([i, j]) => {
    if (keypoints[i] && keypoints[j]) {
      const c1 = keypoints[i].conf !== undefined ? keypoints[i].conf : (keypoints[i][2] || 0);
      const c2 = keypoints[j].conf !== undefined ? keypoints[j].conf : (keypoints[j][2] || 0);

      if (c1 > 0.25 && c2 > 0.25) {
        const x1 = (keypoints[i].x !== undefined ? keypoints[i].x : keypoints[i][0]) * scaleX;
        const y1 = (keypoints[i].y !== undefined ? keypoints[i].y : keypoints[i][1]) * scaleY;
        const x2 = (keypoints[j].x !== undefined ? keypoints[j].x : keypoints[j][0]) * scaleX;
        const y2 = (keypoints[j].y !== undefined ? keypoints[j].y : keypoints[j][1]) * scaleY;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }
  });

  // Draw Skeleton Joints
  keypoints.forEach(kp => {
    const c = kp.conf !== undefined ? kp.conf : (kp[2] || 0);
    if (c > 0.25) {
      const x = (kp.x !== undefined ? kp.x : kp[0]) * scaleX;
      const y = (kp.y !== undefined ? kp.y : kp[1]) * scaleY;

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = jointColor;
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }
  });

  // Corner HUD Tag
  ctx.font = "bold 13px 'Times New Roman', Times, serif";
  ctx.fillStyle = isAccident ? "#dc2626" : "#d97706";
  ctx.fillText(`POSTURE: ${data.posture || 'DETECTING'}`, 14, 24);
}

let emergencyTimerId = null;
let emergencySecondsLeft = 10;
let lastEmergencyTriggerTime = 0;

function updateTrafficLights(riskLevel) {
  const red = document.getElementById("lightRed");
  const amber = document.getElementById("lightAmber");
  const green = document.getElementById("lightGreen");
  const text = document.getElementById("trafficSignalText");
  if (!red || !amber || !green || !text) return;

  red.classList.remove("active-red");
  amber.classList.remove("active-amber");
  green.classList.remove("active-green");

  if (riskLevel === "CRITICAL") {
    red.classList.add("active-red");
    text.textContent = "SIGNAL: CRITICAL / COLLISION ALERT";
    text.className = "text-xs font-bold text-red-400";
  } else if (riskLevel === "WARNING") {
    amber.classList.add("active-amber");
    text.textContent = "SIGNAL: WARNING / UNSTABLE POSTURE";
    text.className = "text-xs font-bold text-amber-400";
  } else {
    green.classList.add("active-green");
    text.textContent = "SIGNAL: NOMINAL UPRIGHT";
    text.className = "text-xs font-bold text-emerald-400";
  }
}

function updateTelemetryCard(data) {
  const postEl = document.getElementById("telemetryPosture");
  const riskEl = document.getElementById("telemetryRisk");
  const angEl = document.getElementById("telemetryAngle");
  const card = document.getElementById("postureCard");
  const navBadge = document.getElementById("navStatusBadge");
  const navText = document.getElementById("navStatusText");

  if (!postEl || !riskEl) return;

  postEl.textContent = data.posture || "NORMAL / UPRIGHT";
  
  if (data.torso_angle !== undefined && data.torso_angle !== null) {
    angEl.textContent = `Torso: ${Number(data.torso_angle).toFixed(1)}°`;
  }

  // Update dynamic traffic light housing
  updateTrafficLights(data.risk_level);

  if (data.risk_level === "CRITICAL") {
    riskEl.className = "text-xs font-bold px-2 py-0.5 rounded bg-red-950/80 text-red-200 border border-red-700";
    riskEl.textContent = "CRITICAL / FALL";
    if (card) card.className = "clean-card rounded-xl p-3 flex items-center justify-between border border-red-800 transition-all";
    if (navBadge) navBadge.className = "flex items-center gap-1.5 text-xs px-2 py-0.5 rounded bg-red-950/60 border border-red-800 text-red-300";
    if (navText) navText.textContent = "Collision Alert";

    // Auto-intercept if fall detected (throttled by 30s)
    const now = Date.now();
    if (now - lastEmergencyTriggerTime > 30000) {
      lastEmergencyTriggerTime = now;
      openEmergencyModal({
        posture: data.posture,
        torso_angle: data.torso_angle
      });
    }
  } else if (data.risk_level === "WARNING") {
    riskEl.className = "text-xs font-bold px-2 py-0.5 rounded bg-amber-950/80 text-amber-200 border border-amber-700";
    riskEl.textContent = "WARNING / LEAN";
    if (card) card.className = "clean-card rounded-xl p-3 flex items-center justify-between border border-amber-800 transition-all";
    if (navBadge) navBadge.className = "flex items-center gap-1.5 text-xs px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800 text-amber-300";
    if (navText) navText.textContent = "Unstable Posture";
  } else {
    riskEl.className = "text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300";
    riskEl.textContent = "NORMAL";
    if (card) card.className = "clean-card rounded-xl p-3 flex items-center justify-between border border-border transition-all";
    if (navBadge) navBadge.className = "flex items-center gap-1.5 text-xs px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-800 text-emerald-300";
    if (navText) navText.textContent = "System Ready";
  }
}

// -------------------------------------------------------------
// 3B. EMERGENCY AMBULANCE DIRECTORY & SOS DISPATCH CONTROLLER
// -------------------------------------------------------------
async function triggerEmergencySOS(customLevel = "CRITICAL_COLLISION") {
  const card = document.getElementById("sosDispatchCard");
  const idEl = document.getElementById("sosDispatchId");
  const unitEl = document.getElementById("sosUnitsAssigned");

  try {
    const res = await fetch("/api/dispatch-sos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        accident_type: customLevel,
        coordinates: "28.6139° N, 77.2090° E (Highway Sector 04)"
      })
    });

    if (!res.ok) throw new Error("SOS Dispatch Failed");

    const data = await res.json();

    if (card) card.classList.remove("hidden");
    if (idEl) idEl.textContent = data.dispatch_id || "SOS-9941";
    if (unitEl) {
      unitEl.textContent = `Assigned: ${data.assigned_units || 'ALS Trauma Team #08'} • Facility: ${data.nearest_hospital || 'Apex Level-1 Trauma'} • ETA: ${data.estimated_arrival_minutes || 6} mins`;
    }

    if (window.lucide) lucide.createIcons();
    
    // Smooth scroll down to ambulance hub if not already in view
    const hub = document.getElementById("ambulance-hub");
    if (hub) {
      hub.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

  } catch (err) {
    console.error("SOS Dispatch error:", err);
    alert(`Emergency SOS Trigger: Connected to Highway Emergency Network. Call 108 for immediate ambulance.`);
  }
}

function openEmergencyModal(info = {}) {
  const modal = document.getElementById("emergencyOverlayModal");
  const desc = document.getElementById("emergencyModalDesc");
  const timer = document.getElementById("emergencyModalTimer");
  if (!modal) return;

  if (desc && info.posture) {
    desc.textContent = `${info.posture} detected (${info.torso_angle ? info.torso_angle.toFixed(1) + '° tilt' : 'ground impact'}). Immediate trauma dispatch recommended.`;
  }

  modal.classList.remove("hidden");
  emergencySecondsLeft = 10;
  if (timer) timer.textContent = `Dispatches in ${emergencySecondsLeft}s`;

  if (emergencyTimerId) clearInterval(emergencyTimerId);
  emergencyTimerId = setInterval(() => {
    emergencySecondsLeft--;
    if (timer) timer.textContent = `Dispatches in ${emergencySecondsLeft}s`;
    if (emergencySecondsLeft <= 0) {
      clearInterval(emergencyTimerId);
      emergencyTimerId = null;
      triggerEmergencySOS("AUTOMATED_RADAR_INTERCEPT");
      closeEmergencyModal();
    }
  }, 1000);

  if (window.lucide) lucide.createIcons();
}

function closeEmergencyModal() {
  const modal = document.getElementById("emergencyOverlayModal");
  if (emergencyTimerId) {
    clearInterval(emergencyTimerId);
    emergencyTimerId = null;
  }
  if (modal) modal.classList.add("hidden");
}


// -------------------------------------------------------------
// 4. WEBCAM RECORDING VIA MEDIARECORDER API
// -------------------------------------------------------------
function toggleRecording(forceState) {
  const targetState = forceState !== undefined ? forceState : !AppState.isRecording;
  const recordBtnText = document.getElementById("recordBtnText");
  const badge = document.getElementById("recordingBadge");
  const timerText = document.getElementById("recordingTimer");
  const canvas = document.getElementById("cameraCanvas");
  const recordedBox = document.getElementById("recordedVideoBox");

  if (targetState) {
    // START RECORDING
    if (!AppState.isCameraActive) return;

    try {
      // Capture the canvas stream so the recorded clip has the 17-keypoint skeleton HUD included!
      const stream = canvas.captureStream(25);
      AppState.recordedChunks = [];

      AppState.mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
          ? "video/webm;codecs=vp9"
          : "video/webm"
      });

      AppState.mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          AppState.recordedChunks.push(e.data);
        }
      };

      AppState.mediaRecorder.onstop = () => {
        const blob = new Blob(AppState.recordedChunks, { type: "video/webm" });
        AppState.recordedVideoBlob = blob;
        const videoUrl = URL.createObjectURL(blob);

        const dlBtn = document.getElementById("downloadRecordBtn");
        if (dlBtn) dlBtn.href = videoUrl;

        const info = document.getElementById("recordedInfo");
        if (info) info.textContent = `${(blob.size / (1024 * 1024)).toFixed(2)} MB • ${AppState.recordingSeconds}s`;

        if (recordedBox) recordedBox.classList.remove("hidden");
        lucide.createIcons();
      };

      AppState.mediaRecorder.start(200);
      AppState.isRecording = true;

      if (recordBtnText) recordBtnText.textContent = "Stop";
      if (badge) badge.classList.remove("hidden");

      // Recording timer
      AppState.recordingSeconds = 0;
      if (timerText) timerText.textContent = "REC 00:00";
      AppState.recordingTimerInterval = setInterval(() => {
        AppState.recordingSeconds++;
        const m = String(Math.floor(AppState.recordingSeconds / 60)).padStart(2, "0");
        const s = String(AppState.recordingSeconds % 60).padStart(2, "0");
        if (timerText) timerText.textContent = `REC ${m}:${s}`;
      }, 1000);

    } catch (err) {
      console.error("Recording error:", err);
      alert(`Recording could not start: ${err.message}`);
      AppState.isRecording = false;
    }

  } else {
    // STOP RECORDING
    AppState.isRecording = false;

    if (AppState.recordingTimerInterval) {
      clearInterval(AppState.recordingTimerInterval);
      AppState.recordingTimerInterval = null;
    }

    if (AppState.mediaRecorder && AppState.mediaRecorder.state !== "inactive") {
      AppState.mediaRecorder.stop();
    }

    if (recordBtnText) recordBtnText.textContent = "Record";
    if (badge) badge.classList.add("hidden");
  }
}

function playRecordedClip() {
  if (!AppState.recordedVideoBlob) return;
  // Switch to video mode and play recorded clip in player
  switchMode("video");
  const player = document.getElementById("uploadedVideoPlayer");
  const placeholder = document.getElementById("uploadedVideoPlaceholder");
  if (player && placeholder) {
    placeholder.classList.add("hidden");
    player.classList.remove("hidden");
    player.src = URL.createObjectURL(AppState.recordedVideoBlob);
    player.play();
  }
}

function takeSnapshot() {
  const canvas = document.getElementById("cameraCanvas");
  if (!canvas) return;

  const dataUrl = canvas.toDataURL("image/png");
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = `Traxion_Snap_${Date.now()}.png`;
  a.click();
}

// -------------------------------------------------------------
// 5. VIDEO FILE UPLOAD & TIMELINE
// -------------------------------------------------------------
function initVideoUpload() {
  const dropArea = document.getElementById("videoDropArea");
  const fileInput = document.getElementById("videoFileInput");

  if (!dropArea || !fileInput) return;

  dropArea.addEventListener("click", () => fileInput.click());

  dropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropArea.classList.add("border-cyan-400", "bg-card");
  });

  dropArea.addEventListener("dragleave", () => {
    dropArea.classList.remove("border-cyan-400", "bg-card");
  });

  dropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    dropArea.classList.remove("border-cyan-400", "bg-card");
    if (e.dataTransfer.files.length > 0) {
      handleVideoFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleVideoFile(e.target.files[0]);
    }
  });
}

async function handleVideoFile(file) {
  if (!file) return;

  const progressBox = document.getElementById("videoUploadProgress");
  const progressText = document.getElementById("videoProgressText");
  const progressBar = document.getElementById("videoProgressBar");
  const player = document.getElementById("uploadedVideoPlayer");
  const placeholder = document.getElementById("uploadedVideoPlaceholder");

  if (progressBox) progressBox.classList.remove("hidden");
  if (progressText) progressText.textContent = `Analyzing ${file.name}...`;

  let pct = 15;
  const timer = setInterval(() => {
    if (pct < 90) {
      pct += 6;
      if (progressBar) progressBar.style.width = `${pct}%`;
    }
  }, 500);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/detect/video", {
      method: "POST",
      body: formData
    });

    clearInterval(timer);

    if (!res.ok) throw new Error("Video analysis failed");

    if (progressBar) progressBar.style.width = "100%";
    const report = await res.json();

    // Play analyzed video
    if (placeholder) placeholder.classList.add("hidden");
    if (player) {
      player.classList.remove("hidden");
      // Append cache buster to guarantee the browser decodes the newly processed stream
      player.src = (report.video_stream_url || `/api/media/output/analyzed_${report.job_id}.mp4`) + "?t=" + Date.now();
      player.load();
      player.play().catch(e => console.log("Autoplay deferred until user interaction:", e));
    }

    // Configure Action Bar & Download Link
    const actionBar = document.getElementById("videoActionBar");
    const dlBtn = document.getElementById("downloadVideoBtn");
    const statusPill = document.getElementById("videoStatusPill");
    const metaText = document.getElementById("videoSummaryMeta");

    if (dlBtn) {
      dlBtn.href = report.download_url || report.video_stream_url;
      const downloadFilename = `Traxion_Analyzed_${report.job_id || 'clip'}.mp4`;
      dlBtn.setAttribute("download", downloadFilename);
    }

    if (statusPill) {
      statusPill.textContent = report.posture || "ANALYSIS COMPLETE";
      if (report.risk_level === "CRITICAL") {
        statusPill.className = "text-xs font-mono font-bold px-2.5 py-1 rounded bg-siren-600 text-white animate-pulse shadow-sm";
      } else if (report.risk_level === "WARNING") {
        statusPill.className = "text-xs font-mono font-bold px-2.5 py-1 rounded bg-amber-500 text-black";
      } else {
        statusPill.className = "text-xs font-mono font-bold px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
      }
    }

    if (metaText) {
      metaText.textContent = `${report.analyzed_frames || 28} Frames Analyzed • H.264 Web Stream • ${report.processing_time_sec || 0}s`;
    }

    if (actionBar) {
      actionBar.classList.remove("hidden");
    }
    lucide.createIcons();

    updateTelemetryCard(report);
    update3DTraumaHighlights(report.impacted_zones || []);
    renderTimelineEvents(report.timeline || []);

  } catch (err) {
    alert(`Video Error: ${err.message}`);
  } finally {
    clearInterval(timer);
    setTimeout(() => {
      if (progressBox) progressBox.classList.add("hidden");
    }, 1000);
  }
}

function renderTimelineEvents(events = []) {
  const container = document.getElementById("timelineEventsContainer");
  const list = document.getElementById("timelineList");
  const player = document.getElementById("uploadedVideoPlayer");
  if (!container || !list) return;

  if (events.length === 0) {
    container.classList.add("hidden");
    return;
  }

  container.classList.remove("hidden");
  list.innerHTML = events.map((ev) => {
    const isCritical = ev.risk_level === "CRITICAL";
    const badge = isCritical 
      ? "bg-siren-600 text-white animate-pulse" 
      : (ev.risk_level === "WARNING" ? "bg-amber-500 text-black" : "bg-emerald-500/20 text-emerald-400");
    
    const timeStr = typeof ev.time_sec === 'number' ? `${ev.time_sec.toFixed(1)}s` : ev.timestamp;

    return `
      <div onclick="seekVideo(${ev.time_sec || 0})" class="p-2 rounded-lg bg-void border border-border hover:border-cyan-400/60 cursor-pointer flex items-center justify-between text-xs font-mono transition-all">
        <div class="flex items-center gap-2">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${badge}">${timeStr}</span>
          <span class="font-bold text-slate-200">${ev.posture}</span>
        </div>
        <span class="text-[10px] text-cyan-400">JUMP ➔</span>
      </div>
    `;
  }).join("");
}

function seekVideo(seconds) {
  const player = document.getElementById("uploadedVideoPlayer");
  if (player) {
    player.currentTime = seconds;
    player.play();
  }
}

function replayAnalyzedVideo() {
  const player = document.getElementById("uploadedVideoPlayer");
  if (player) {
    player.currentTime = 0;
    player.play().catch(() => {});
  }
}

async function loadSampleVideoDirect(event) {
  event.stopPropagation();
  try {
    const res = await fetch("/static/samples/sample_accident.mp4");
    if (!res.ok) throw new Error("Sample file not found");
    const blob = await res.blob();
    const file = new File([blob], "sample_accident.mp4", { type: "video/mp4" });
    handleVideoFile(file);
  } catch (err) {
    alert(`Could not load sample: ${err.message}`);
  }
}

// -------------------------------------------------------------
// 6. INITIALIZATION
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  init3DBodyModel();
  initVideoUpload();
  console.log("🛡️ Traxion AI interface loaded.");
});
