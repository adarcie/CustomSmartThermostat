import RPi.GPIO as GPIO
import time

# ---------- PIN CONFIG (your choices) ----------
MOTOR_PINS = [17, 18, 27, 22]   # BCM pins to your stepper driver
MIN_PIN = 16                    # MIN endstop
MAX_PIN = 26                    # MAX endstop

DELAY = 0.002       # step delay (speed)
BACKOFF_STEPS = 40  # how far to reverse when a switch is hit

# Standard half-step sequence
SEQUENCE = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1]
]

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Motor outputs
    for p in MOTOR_PINS:
        GPIO.setup(p, GPIO.OUT)
        GPIO.output(p, 0)

    # Limit switches: active-low with internal pull-ups (2-wire wiring)
    GPIO.setup(MIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(MAX_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def release_coils():
    for p in MOTOR_PINS:
        GPIO.output(p, 0)

def apply_step(step):
    for pin, val in zip(MOTOR_PINS, step):
        GPIO.output(pin, val)

def limit_hit():
    """Return True if either switch is pressed (active-low)."""
    return (GPIO.input(MIN_PIN) == GPIO.LOW) or (GPIO.input(MAX_PIN) == GPIO.LOW)

def test_limits_until_hit(direction=1):
    """
    STANDALONE TEST:
      - Rotate continuously in `direction`
      - Stop immediately when either limit switch is hit
      - Reverse briefly (backoff)
      - Stop and release coils

    direction: 1 = forward, -1 = reverse
    """
    setup_gpio()
    print(f"[LIMIT TEST] Starting, direction={direction}")

    seq = SEQUENCE if direction >= 0 else list(reversed(SEQUENCE))
    seq_len = len(seq)
    idx = 0

    try:
        # ---- MAIN ROTATION LOOP ----
        while True:
            if limit_hit():
                print("[LIMIT TEST] Switch triggered! Backing off...")
                break

            apply_step(seq[idx])
            time.sleep(DELAY)
            idx = (idx + 1) % seq_len

        # ---- BACKOFF (reverse briefly) ----
        back_seq = list(reversed(seq))  # opposite direction
        back_len = len(back_seq)

        for _ in range(BACKOFF_STEPS):
            apply_step(back_seq[idx])
            time.sleep(DELAY)
            idx = (idx + 1) % back_len

        print("[LIMIT TEST] Done.")

    finally:
        release_coils()
        GPIO.cleanup()

# ---------- If run directly ----------
if __name__ == "__main__":
    # Try one direction first; if it's wrong, run again with -1
    test_limits_until_hit(direction=1)
