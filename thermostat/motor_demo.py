from stepper import StepperMotor
import time

motor = StepperMotor([17, 18, 27, 22], delay=0.002)

print("CW")
motor.move_steps(512, direction=1)
time.sleep(1)

print("CCW")
motor.move_steps(512, direction=-1)

motor.cleanup()