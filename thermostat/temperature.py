import glob
import time

class TemperatureSensor:
    def __init__(self):
        devices = glob.glob('/sys/bus/w1/devices/28-*')
        if not devices:
            raise RuntimeError("No DS18B20 sensor found")
        self.device_file = devices[0] + '/w1_slave'

    def read_celsius(self):
        with open(self.device_file, 'r') as f:
            lines = f.readlines()

        if lines[0].strip()[-3:] != 'YES':
            return None

        equals_pos = lines[1].find('t=')
        if equals_pos == -1:
            return None

        temp_c = float(lines[1][equals_pos+2:]) / 1000.0
        return round(temp_c, 2)

if __name__ == "__main__":
    sensor = TemperatureSensor()
    while True:
        temp = sensor.read_celsius()
        print("Temp:", temp, "°C")
        time.sleep(2)

