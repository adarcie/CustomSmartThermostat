import json
import paho.mqtt.client as mqtt

BROKER_IP = "192.168.4.26"  # Pi 4 IP

class MqttBridge:
    def __init__(self):
        self.temps = {}
        self.states = {}

        self.client = mqtt.Client(
            client_id="flask-dashboard",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        self.client.on_message = self._on_message

        self.client.connect(BROKER_IP, 1883, 60)
        self.client.subscribe("thermostat/+/temperature")
        self.client.subscribe("thermostat/+/state")
        self.client.loop_start()

    def _on_message(self, client, userdata, msg):
        tid = msg.topic.split("/")[1]
        payload = json.loads(msg.payload.decode())

        if msg.topic.endswith("/temperature"):
            self.temps[tid] = payload["temperature"]

        elif msg.topic.endswith("/state"):
            self.states[tid] = payload

    def set_setpoint(self, tid, value):
        self.client.publish(
            f"thermostat/{tid}/setpoint",
            value
        )
