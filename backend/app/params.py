"""Backend-owned experimental parameters (SRS section 4).
These constants/ranges are the single source of truth for every
experimental parameter used by Phase 2/3/4. Both the real-trial API
(routers/trials.py) and the demo API (routers/demo.py) read from here.
"""

# Phase 2 (Direct Resolution): speed = mouse_position * 2 + noise
PHASE2_NOISE_RANGE = (-0.1, 0.1)

# Phase 3 (Speed Estimation): system-controlled actual playback speed
# PHASE3_ACTUAL_SPEED_RANGE = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]

# Phase 4 (Threshold and Tolerance) -- matches the SRS example exactly:
#   Delay 3000 ms / Every 100 ms / Speed += 0.01
PHASE4_DELAY_MS = 2000
PHASE4_TICK_MS = 100 
PHASE4_STEP = 0.01
