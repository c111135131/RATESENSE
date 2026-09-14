"""Backend-controlled experiment state machine (SRS 8.9).
The frontend never decides the next page -- it always asks the backend.
"""

STATE_TRANSITIONS = {
    "home": "terms-agreement",
    "terms-agreement": "User-Quetionaire",
    "User-Quetionaire": "procedure",

    "procedure": "phase1-start",

    "phase1-start": "phase1-instruction",
    "phase1-instruction": "phase1-recording",
    "phase1-recording": "phase1-complete",
    "phase1-complete": "phase2-start",

    "phase2-start": "phase2-instruction",
    "phase2-instruction": "phase2-demo",
    "phase2-demo": "phase2-demo-complete",
    "phase2-demo-complete": "phase2-realtest",
    "phase2-realtest": "phase2-complete",
    "phase2-complete": "phase3-start",

    "phase3-start": "phase3-instruction",
    "phase3-instruction": "phase3-demo",
    "phase3-demo": "phase3-demo-complete",
    "phase3-demo-complete": "phase3-realtest",
    "phase3-realtest": "phase3-complete",
    "phase3-complete": "phase4-start",

    "phase4-start": "phase4-instruction",
    "phase4-instruction": "phase4-demo",
    "phase4-demo": "phase4-demo-complete",
    "phase4-demo-complete": "phase4-realtest",
    "phase4-realtest": "phase4-complete",
    "phase4-complete": "completed",
}

# Number of real trials per phase (5 predefined videos + 1 self-recorded video)
TRIALS_PER_PHASE = 6

# Which phase number a given real-test/demo state belongs to
PHASE_OF_STATE = {
    "phase1-recording": 1,
    "phase2-demo": 2, "phase2-realtest": 2,
    "phase3-demo": 3, "phase3-realtest": 3,
    "phase4-demo": 4, "phase4-realtest": 4,
}


def next_state(current_state: str) -> str:
    return STATE_TRANSITIONS.get(current_state, current_state)
