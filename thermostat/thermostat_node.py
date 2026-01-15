import time
import json
import glob
import paho.mqtt.client as mqtt
from stepper import StepperMotor

BROKER_IP = "192.168.4.26"
THERMO_ID = "livingroom"

TEMP_TOPIC = f"thermostat/{THERMO_ID}/temperature"
STATE_TOPIC = f"thermostat/{THERMO_ID}/state"
SETPOINT_TOPIC = f"thermostat/{THERMO_ID}/setpoint"
SETTINGS_TOPIC = f"thermostat/{THERMO_ID}/settings"

# Default settings
setpoint = 21.0
hysteresis = 0.5
steps_on = 1000
steps_off = 1000

heating = False

# DS18B20 setup
base_dir = "/sys/bus/w1/devices/"
device_folder = glob.glob(base_dir + "28-*")[0]
device_file = device_folder + "/w1_slave"

def read_temp():
    with open(device_file, "r") as f:
        lines = f.readlines()
    if lines[0].strip()[-3:] != "YES":
        return None
    temp_string = lines[1].split("t=")[-1]
    return float(temp_string) / 1000.0

MOTOR_PINS = [17, 18, 27, 22]  # BCM pins
motor = StepperMotor(MOTOR_PINS, delay=0.002)

def on_connect(client, userdata, flags, rc):
    print("Thermostat connected to MQTT with code", rc)
    client.subscribe([
        (SETPOINT_TOPIC, 1),
        (SETTINGS_TOPIC, 1)
    ])

def on_message(client, userdata, msg):
    global setpoint, hysteresis, steps_on, steps_off

    if msg.topic == SETPOINT_TOPIC:
        setpoint = float(msg.payload.decode())
        print("New setpoint:", setpoint)

    elif msg.topic == SETTINGS_TOPIC:
        data = json.loads(msg.payload.decode())
        hysteresis = data["hysteresis"]
        steps_on = data["steps_on"]
        steps_off = data["steps_off"]
        print("Settings updated:", data)

client = mqtt.Client(client_id=f"thermostat-{THERMO_ID}")
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_IP, 1883, 60)
client.loop_start()

print("Thermostat node running")

while True:
    temp = read_temp()
    if temp is None:
        time.sleep(2)
        continue

    # Publish temperature
    client.publish(
        TEMP_TOPIC,
        json.dumps({"temperature": round(temp, 2)}),
        qos=1
    )

    # Hysteresis logic
    if not heating and temp < (setpoint - hysteresis):
        heating = True
        motor.move_steps(steps_on, direction=1)
        print("Heating ON")

    elif heating and temp > (setpoint + hysteresis):
        heating = False
        motor.move_steps(steps_off, direction=-1)
        print("Heating OFF")

    # Publish state
    client.publish(
        STATE_TOPIC,
        json.dumps({
            "setpoint": setpoint,
            "heating": heating
        }),
        qos=1
    )

    time.sleep(5)
