import RPi.GPIO as GPIO
import time
import threading


class StepperMotor:
    # half-step sequence (8 steps)
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

    def __init__(self, pins, delay=0.002):
        """
        pins: list of 4 BCM GPIO pins, e.g. [17,18,27,22]
        delay: seconds between micro-steps
        """
        self.pins = list(pins)
        self.delay = float(delay)
        self._running = False
        self._lock = threading.Lock()
        self._idx = 0  # persistent phase index

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for p in self.pins:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, 0)

    def _apply(self, step):
        for pin, val in zip(self.pins, step):
            GPIO.output(pin, val)

    def move_steps(self, steps, direction=1):
        """
        Move exactly `steps` half-steps.
        Direction: 1 = CW, -1 = CCW
        """
        if steps <= 0:
            return

        seq = self.SEQUENCE if direction >= 0 else list(reversed(self.SEQUENCE))
        seq_len = len(seq)

        for _ in range(steps):
            step = seq[self._idx]
            self._apply(step)
            time.sleep(self.delay)
            self._idx = (self._idx + 1) % seq_len

        self._release()

    def start_continuous(self, direction=1):
        """Start continuous motion in background."""
        with self._lock:
            if self._running:
                return
            self._running = True

        def run():
            seq = self.SEQUENCE if direction >= 0 else list(reversed(self.SEQUENCE))
            seq_len = len(seq)
            try:
                while True:
                    with self._lock:
                        if not self._running:
                            break
                    self._apply(seq[self._idx])
                    time.sleep(self.delay)
                    self._idx = (self._idx + 1) % seq_len
            finally:
                self._release()

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        with self._lock:
            self._running = False
        time.sleep(self.delay * 2)
        self._release()

    def _release(self):
        for p in self.pins:
            GPIO.output(p, 0)

    def cleanup(self):
        self.stop()
        GPIO.cleanup(self.pins)
