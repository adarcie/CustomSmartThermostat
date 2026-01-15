class ThermostatController:
    def __init__(self, motor, sensor, setpoint=21.0, hysteresis=0.5):
        self.motor = motor
        self.sensor = sensor
        self.setpoint = setpoint
        self.hysteresis = hysteresis
        self.heating = False

    def set_setpoint(self, value):
        print("Setpoint updated to", value)
        self.setpoint = value

    def update(self):
        temp = self.sensor.read_celsius()
        if temp is None:
            return None

        if temp < self.setpoint - self.hysteresis:
            if not self.heating:
                self.heating = True
                self.on_heat_on()
        elif temp > self.setpoint + self.hysteresis:
            if self.heating:
                self.heating = False
                self.on_heat_off()

        return temp

    def on_heat_on(self):
        print("HEAT ON")
        self.motor.move_steps(200)
        # motor.move_to_on()

    def on_heat_off(self):
        print("HEAT OFF")
        self.motor.move_steps(200,direction=-1)
        # motor.move_to_off()

