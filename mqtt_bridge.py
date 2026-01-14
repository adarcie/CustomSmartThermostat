import json
import threading
import paho.mqtt.client as mqtt

BROKER_IP = "192.168.4.26"   # <-- PI IP
BROKER_PORT = 1883
THERMO_ID = "livingroom"

# Single source of truth for Flask
thermostat_state = {
    "temperature": None,
    "setpoint": None,
    "heating": None
}


class MqttBridge:
    def __init__(self):
        self.client = mqtt.Client(client_id="flask-dashboard")

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(BROKER_IP, BROKER_PORT, 60)

        thread = threading.Thread(
            target=self.client.loop_forever,
            daemon=True
        )
        thread.start()

    def on_connect(self, client, userdata, flags, rc):
        print("Flask connected to MQTT, rc =", rc)
        client.subscribe(f"thermostat/{THERMO_ID}/#", qos=1)

    def on_message(self, client, userdata, msg):
        global thermostat_state

        topic = msg.topic
        payload = msg.payload.decode()

        if topic == f"thermostat/{THERMO_ID}/temperature":
            data = json.loads(payload)
            thermostat_state["temperature"] = data["temperature"]

        elif topic == f"thermostat/{THERMO_ID}/state":
            data = json.loads(payload)
            thermostat_state["setpoint"] = data["setpoint"]
            thermostat_state["heating"] = data["heating"]

    def publish_setpoint(self, value):
        self.client.publish(
            f"thermostat/{THERMO_ID}/setpoint",
            value,
            qos=1,
            retain=True
        )
