import RPi.GPIO as GPIO
import time
import threading


class StepperMotor:
    # half-step sequence (8 steps) - SAME AS BEFORE
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

    def __init__(
        self,
        pins,
        delay=0.002,
        min_limit_pin=16,
        max_limit_pin=26,
        enable_limits=True,
        backoff_steps=200,
        verbose=False,
    ):
        """
        pins: list of 4 BCM GPIO pins, e.g. [17,18,27,22]
        delay: seconds between micro-steps

        Limit switches (2-wire recommended, active-low):
          - min_limit_pin: GPIO16
          - max_limit_pin: GPIO26
          - enable_limits: enable/disable limit behavior
          - backoff_steps: steps to reverse when a switch is pressed
        """
        self.pins = list(pins)
        self.delay = float(delay)

        self.min_limit_pin = min_limit_pin
        self.max_limit_pin = max_limit_pin
        self.enable_limits = bool(enable_limits)
        self.backoff_steps = int(backoff_steps)
        self.verbose = bool(verbose)

        self._running = False
        self._lock = threading.Lock()
        self._idx = 0  # SAME AS BEFORE

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # motor outputs (SAME AS BEFORE)
        for p in self.pins:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, 0)

        # limit inputs (active-low with pull-ups)
        if self.enable_limits:
            if self.min_limit_pin is not None:
                GPIO.setup(self.min_limit_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            if self.max_limit_pin is not None:
                GPIO.setup(self.max_limit_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        if self.verbose:
            print(
                f"[StepperMotor] pins={self.pins} delay={self.delay} "
                f"limits={'on' if self.enable_limits else 'off'} "
                f"MIN={self.min_limit_pin} MAX={self.max_limit_pin} "
                f"backoff_steps={self.backoff_steps}"
            )

    def _apply(self, step):
        for pin, val in zip(self.pins, step):
            GPIO.output(pin, val)

    def _release(self):
        for p in self.pins:
            GPIO.output(p, 0)

    def _limit_hit(self) -> bool:
        """True if either switch is pressed (active-low)."""
        if not self.enable_limits:
            return False

        if self.min_limit_pin is not None and GPIO.input(self.min_limit_pin) == GPIO.LOW:
            return True
        if self.max_limit_pin is not None and GPIO.input(self.max_limit_pin) == GPIO.LOW:
            return True
        return False

    def _raw_move_steps(self, steps: int, direction: int):
        """
        Move exactly `steps` half-steps WITHOUT checking limit switches.
        Uses the SAME stepping approach as the original code.
        """
        if steps <= 0:
            return

        seq = self.SEQUENCE if direction >= 0 else list(reversed(self.SEQUENCE))
        seq_len = len(seq)

        for _ in range(int(steps)):
            step = seq[self._idx]
            self._apply(step)
            time.sleep(self.delay)
            self._idx = (self._idx + 1) % seq_len

    def _backoff_and_stop(self, direction: int):
        """
        Simple behavior:
          if a switch is pressed -> reverse briefly and stop.
        Uses SAME stepping as normal motion, but ignores limits (no recursion).
        """
        reverse_dir = -1 if direction >= 0 else 1

        if self.verbose:
            min_state = GPIO.input(self.min_limit_pin) if (self.enable_limits and self.min_limit_pin is not None) else None
            max_state = GPIO.input(self.max_limit_pin) if (self.enable_limits and self.max_limit_pin is not None) else None
            print(f"[LIMIT] HIT (MIN={min_state}, MAX={max_state}) -> backoff {self.backoff_steps} steps dir={reverse_dir}")

        self._raw_move_steps(self.backoff_steps, reverse_dir)
        self._release()

    def move_steps(self, steps, direction=1):
        """
        Original behavior + limit handling:
          - move exactly `steps` half-steps
          - if either switch is pressed during motion:
              reverse briefly and stop
        """
        if steps <= 0:
            return

        seq = self.SEQUENCE if direction >= 0 else list(reversed(self.SEQUENCE))
        seq_len = len(seq)

        for _ in range(int(steps)):
            if self._limit_hit():
                self._backoff_and_stop(direction)
                return

            step = seq[self._idx]
            self._apply(step)
            time.sleep(self.delay)
            self._idx = (self._idx + 1) % seq_len

        self._release()

    def start_continuous(self, direction=1):
        """Start continuous motion in background, stop+backoff on limit hit."""
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

                    if self._limit_hit():
                        with self._lock:
                            self._running = False
                        self._backoff_and_stop(direction)
                        return

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

    def cleanup(self):
        self.stop()
        pins_to_cleanup = list(self.pins)
        if self.enable_limits:
            if self.min_limit_pin is not None:
                pins_to_cleanup.append(self.min_limit_pin)
            if self.max_limit_pin is not None:
                pins_to_cleanup.append(self.max_limit_pin)
        GPIO.cleanup(pins_to_cleanup)
